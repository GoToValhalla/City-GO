"""
Публичный выбор изображения места: только approved/active из place_images
или доверенный legacy place.image_url.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from models.place_image import (
    PUBLIC_PLACE_IMAGE_STATUSES,
    PLACE_IMAGE_STATUS_ACTIVE,
    PlaceImage,
)

TRUSTED_LEGACY_IMAGE_SOURCES = frozenset({"manual", "editorial", "verified_manual", "admin", "trusted_manual"})


@dataclass(frozen=True)
class PublicPlaceImage:
    image_url: str
    image_id: int | None
    image_source_type: str | None
    image_attribution: str | None
    image_license: str | None
    image_confidence: float | None
    image_status: str | None
    image_reviewed_at: datetime | None


def _image_to_public(image: PlaceImage) -> PublicPlaceImage:
    return PublicPlaceImage(
        image_url=image.image_url,
        image_id=image.id,
        image_source_type=image.source_type,
        image_attribution=image.attribution,
        image_license=image.license,
        image_confidence=image.confidence,
        image_status=image.status,
        image_reviewed_at=image.reviewed_at,
    )


def _pick_best_image(images: list[PlaceImage]) -> PlaceImage | None:
    public_images = [image for image in images if image.status in PUBLIC_PLACE_IMAGE_STATUSES]
    if not public_images:
        return None
    primary = next((image for image in public_images if image.is_primary), None)
    if primary is not None:
        return primary
    return sorted(public_images, key=lambda image: image.id)[0]


def resolve_public_place_image(db: Session, place: Place) -> PublicPlaceImage | None:
    images = (
        db.query(PlaceImage)
        .filter(
            PlaceImage.place_id == place.id,
            PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES)),
        )
        .order_by(PlaceImage.is_primary.desc(), PlaceImage.id.asc())
        .all()
    )
    selected = _pick_best_image(images)
    if selected is not None:
        return _image_to_public(selected)

    legacy_source = (place.source or "").strip().lower()
    if place.image_url and legacy_source in TRUSTED_LEGACY_IMAGE_SOURCES:
        return PublicPlaceImage(
            image_url=place.image_url,
            image_id=None,
            image_source_type=legacy_source or "manual",
            image_attribution=None,
            image_license=None,
            image_confidence=None,
            image_status="legacy",
            image_reviewed_at=place.last_verified_at,
        )
    return None


def resolve_public_place_images_bulk(db: Session, places: list[Place]) -> dict[int, PublicPlaceImage | None]:
    if not places:
        return {}

    place_ids = [place.id for place in places]
    rows = (
        db.query(PlaceImage)
        .filter(
            PlaceImage.place_id.in_(place_ids),
            PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES)),
        )
        .order_by(PlaceImage.is_primary.desc(), PlaceImage.id.asc())
        .all()
    )

    by_place: dict[int, list[PlaceImage]] = {}
    for row in rows:
        by_place.setdefault(row.place_id, []).append(row)

    result: dict[int, PublicPlaceImage | None] = {}
    for place in places:
        selected = _pick_best_image(by_place.get(place.id, []))
        if selected is not None:
            result[place.id] = _image_to_public(selected)
            continue

        legacy_source = (place.source or "").strip().lower()
        if place.image_url and legacy_source in TRUSTED_LEGACY_IMAGE_SOURCES:
            result[place.id] = PublicPlaceImage(
                image_url=place.image_url,
                image_id=None,
                image_source_type=legacy_source or "manual",
                image_attribution=None,
                image_license=None,
                image_confidence=None,
                image_status="legacy",
                image_reviewed_at=place.last_verified_at,
            )
        else:
            result[place.id] = None

    return result


def get_public_primary_image(db: Session, place_id: int) -> PublicPlaceImage | None:
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        return None
    return resolve_public_place_image(db, place)


def place_has_public_image(db: Session, place_id: int) -> bool:
    return (
        db.query(PlaceImage.id)
        .filter(
            PlaceImage.place_id == place_id,
            PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES)),
        )
        .first()
        is not None
    )


def clear_primary_flags(db: Session, place_id: int, *, except_image_id: int | None = None) -> None:
    query = db.query(PlaceImage).filter(PlaceImage.place_id == place_id, PlaceImage.is_primary.is_(True))
    if except_image_id is not None:
        query = query.filter(PlaceImage.id != except_image_id)
    for image in query.all():
        image.is_primary = False


def activate_approved_image(image: PlaceImage) -> None:
    if image.status not in PUBLIC_PLACE_IMAGE_STATUSES:
        image.status = PLACE_IMAGE_STATUS_ACTIVE
