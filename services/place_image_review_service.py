"""
Очередь проверки фотографий мест.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.place import Place
from models.place_image import (
    PLACE_IMAGE_STATUS_ACTIVE,
    PLACE_IMAGE_STATUS_APPROVED,
    PLACE_IMAGE_STATUS_NEEDS_REVIEW,
    PLACE_IMAGE_STATUS_REJECTED,
    PlaceImage,
)
from services.admin_audit_service import write_admin_audit_log
from services.place_public_image_service import (
    activate_approved_image,
    clear_primary_flags,
)

PUBLIC_IMAGE_STATUSES = {PLACE_IMAGE_STATUS_APPROVED, PLACE_IMAGE_STATUS_ACTIVE}


def get_pending_place_images(
    db: Session,
    *,
    city_slug: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    query = (
        db.query(PlaceImage)
        .join(Place, Place.id == PlaceImage.place_id)
        .outerjoin(City, City.id == Place.city_id)
        .options(joinedload(PlaceImage.place).joinedload(Place.city))
        .filter(
            or_(
                PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW,
                (PlaceImage.status == PLACE_IMAGE_STATUS_APPROVED) & PlaceImage.reviewed_at.is_(None),
            )
        )
        .order_by(PlaceImage.created_at.asc(), PlaceImage.id.asc())
    )

    if city_slug:
        query = query.filter(City.slug == city_slug)

    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    items = [_pending_item_payload(image) for image in rows]
    return items, total


def _pending_item_payload(image: PlaceImage) -> dict[str, object]:
    place = image.place
    city = place.city if place is not None else None
    return {
        "image_id": image.id,
        "place_id": image.place_id,
        "place_title": place.title if place else "",
        "place_slug": place.slug if place else "",
        "city_slug": city.slug if city else None,
        "place_address": place.address if place else None,
        "place_category": place.category if place else None,
        "place_lat": place.lat if place else 0.0,
        "place_lng": place.lng if place else 0.0,
        "image_url": image.image_url,
        "thumbnail_url": image.thumbnail_url,
        "source_type": image.source_type,
        "source_url": image.source_url,
        "attribution": image.attribution,
        "license": image.license,
        "confidence": image.confidence,
        "status": image.status,
        "created_at": image.created_at,
    }


def _get_image_or_raise(db: Session, image_id: int) -> PlaceImage:
    image = db.query(PlaceImage).filter(PlaceImage.id == image_id).first()
    if image is None:
        raise LookupError(f"PlaceImage {image_id} not found")
    return image


def approve_place_image(
    db: Session,
    image_id: int,
    actor: str = "admin",
    comment: str | None = None,
    commit: bool = True,
) -> PlaceImage:
    """Одобряет фото и пишет audit event. actor берётся из auth context."""
    image = _get_image_or_raise(db, image_id)
    now = datetime.utcnow()

    old_status = image.status
    image.status = PLACE_IMAGE_STATUS_APPROVED
    image.reviewed_by = actor
    image.reviewed_at = now
    image.review_comment = comment or "Manually confirmed"
    image.updated_at = now

    has_primary = (
        db.query(PlaceImage.id)
        .filter(
            PlaceImage.place_id == image.place_id,
            PlaceImage.is_primary.is_(True),
            PlaceImage.status.in_(tuple(PUBLIC_IMAGE_STATUSES)),
            PlaceImage.id != image.id,
        )
        .first()
        is not None
    )
    if not has_primary:
        clear_primary_flags(db, image.place_id, except_image_id=image.id)
        image.is_primary = True

    _sync_place_image_url(db, image.place_id)

    write_admin_audit_log(
        db,
        actor=actor,
        action="approve_place_image",
        entity_type="place_image",
        entity_id=image.id,
        old_value={"status": old_status},
        new_value={"status": image.status, "reviewed_by": actor},
    )

    if commit:
        db.commit()
        db.refresh(image)
    return image


def reject_place_image(
    db: Session,
    image_id: int,
    actor: str = "admin",
    comment: str | None = None,
    commit: bool = True,
) -> PlaceImage:
    """Отклоняет фото и пишет audit event. actor берётся из auth context."""
    image = _get_image_or_raise(db, image_id)
    now = datetime.utcnow()

    old_status = image.status
    image.status = PLACE_IMAGE_STATUS_REJECTED
    image.is_primary = False
    image.reviewed_by = actor
    image.reviewed_at = now
    image.review_comment = comment or "Manually rejected"
    image.updated_at = now

    _sync_place_image_url(db, image.place_id)

    write_admin_audit_log(
        db,
        actor=actor,
        action="reject_place_image",
        entity_type="place_image",
        entity_id=image.id,
        old_value={"status": old_status},
        new_value={"status": image.status, "reviewed_by": actor},
    )

    if commit:
        db.commit()
        db.refresh(image)
    return image


def bulk_review_place_images(
    db: Session,
    image_ids: list[int],
    *,
    action: str,
    actor: str,
    comment: str | None = None,
) -> tuple[list[PlaceImage], list[int]]:
    if action not in {"approve", "reject"}:
        raise ValueError("Unsupported photo review action")
    unique_ids = list(dict.fromkeys(image_ids))
    existing = {image.id for image in db.query(PlaceImage).filter(PlaceImage.id.in_(unique_ids)).all()}
    processed: list[PlaceImage] = []
    for image_id in unique_ids:
        if image_id not in existing:
            continue
        if action == "approve":
            processed.append(approve_place_image(db, image_id, actor=actor, comment=comment, commit=False))
        else:
            processed.append(reject_place_image(db, image_id, actor=actor, comment=comment, commit=False))
    db.commit()
    for image in processed:
        db.refresh(image)
    return processed, [image_id for image_id in unique_ids if image_id not in existing]


def set_primary_place_image(db: Session, image_id: int, actor: str = "admin") -> PlaceImage:
    """Устанавливает фото как основное и пишет audit event."""
    image = _get_image_or_raise(db, image_id)
    if image.status not in PUBLIC_IMAGE_STATUSES:
        raise ValueError("Only approved/active images can be set as primary")

    clear_primary_flags(db, image.place_id, except_image_id=image.id)
    image.is_primary = True
    activate_approved_image(image)
    image.updated_at = datetime.utcnow()

    _sync_place_image_url(db, image.place_id)

    write_admin_audit_log(
        db,
        actor=actor,
        action="set_primary_place_image",
        entity_type="place_image",
        entity_id=image.id,
        new_value={"is_primary": True, "status": image.status},
    )

    db.commit()
    db.refresh(image)
    return image


def _sync_place_image_url(db: Session, place_id: int) -> None:
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        return

    image = (
        db.query(PlaceImage)
        .filter(
            PlaceImage.place_id == place_id,
            PlaceImage.status.in_(tuple(PUBLIC_IMAGE_STATUSES)),
        )
        .order_by(PlaceImage.is_primary.desc(), PlaceImage.id.asc())
        .first()
    )
    place.image_url = image.image_url if image is not None else None
