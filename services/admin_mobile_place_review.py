from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_read_service import build_place_read
from services.place_verification_mutation import verify_locked_place
from services.publication_state_writer import (
    REASON_ADMIN_DEFER,
    REASON_ADMIN_REJECT,
    REASON_NEEDS_MANUAL_REVIEW,
    transition_place_publication,
)
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES
from services.system_log_service import write_system_log

MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
NON_ROUTE_CATEGORIES = HARD_EXCLUDED_CATEGORIES
NON_ROUTE_LAYERS = {"service", "transport", "utility"}
TRUSTED_ADDRESS_CONFIDENCE = 0.85
TRUSTED_PLACE_QUALITY_SCORE = 65
OFFICIAL_ADDRESS_SOURCES = {
    "official", "official_site", "official_website", "website", "site",
    "business_site", "provider_official",
}


def list_review_cities(db: Session) -> dict[str, object]:
    cities = db.query(City).order_by(City.name.asc(), City.slug.asc()).all()
    counts = _publication_counts(db, [int(city.id) for city in cities])
    items = []
    for city in cities:
        city_counts = counts.get(int(city.id), {})
        needs_review = sum(int(city_counts.get(status, 0)) for status in MANUAL_REVIEW_STATUSES)
        auto_backlog = sum(int(city_counts.get(status, 0)) for status in AUTO_BACKLOG_STATUSES)
        if needs_review:
            items.append({
                "id": city.id, "slug": city.slug, "name": city.name,
                "needs_review": needs_review, "rejected": 0,
                "auto_backlog": auto_backlog,
            })
    return {"items": items, "total": len(items)}


def _publication_counts(db: Session, city_ids: list[int]) -> dict[int, dict[str, int]]:
    if not city_ids:
        return {}
    rows = (
        db.query(Place.city_id, Place.publication_status, func.count(Place.id))
        .filter(Place.city_id.in_(city_ids))
        .group_by(Place.city_id, Place.publication_status).all()
    )
    result: dict[int, dict[str, int]] = {}
    for city_id, status, count in rows:
        result.setdefault(int(city_id), {})[str(status or "unknown")] = int(count or 0)
    return result


def next_review_place(db: Session, city_slug: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return {"city": None, "remaining": 0, "place": None}
    query = db.query(Place).filter(
        Place.city_id == city.id,
        Place.publication_status.in_(MANUAL_REVIEW_STATUSES),
    )
    total = query.count()
    place = query.order_by(Place.updated_at.asc(), Place.id.asc()).first()
    return {
        "city": {"id": city.id, "slug": city.slug, "name": city.name},
        "remaining": total,
        "place": place_payload(db, place) if place else None,
    }


def rejected_places(db: Session, city_slug: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return {"items": [], "total": 0, "city": None}
    items = (
        db.query(Place)
        .filter(Place.city_id == city.id, Place.publication_status == "rejected")
        .order_by(Place.updated_at.desc(), Place.id.desc()).limit(100).all()
    )
    return {
        "items": [place_payload(db, item) for item in items],
        "total": len(items),
        "city": {"id": city.id, "slug": city.slug, "name": city.name},
    }


def _locked_place(db: Session, place_id: int) -> Place | None:
    return (
        db.query(Place).filter(Place.id == place_id)
        .with_for_update().populate_existing().one_or_none()
    )


def publish_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    place = _locked_place(db, place_id)
    if place is None:
        return {"action": "not_found", "place": None}
    blockers = publication_blockers(place)
    if blockers:
        raise HTTPException(422, "; ".join(blockers))
    try:
        apply_admin_city_publication_place(
            db, place, actor=actor, source="mobile_review",
            reason="published from moderation", lock_place=False,
        )
        verify_locked_place(
            db, place, actor=actor, reason="published from moderation",
            action="mobile_review_verify", verification_status="trusted",
            verification_source="mobile_review", verification_method="manual_moderation",
        )
        audit(db, place, actor, "mobile_review_publish")
        db.commit()
        db.refresh(place)
        return {"action": "published", "place": place_payload(db, place)}
    except Exception:
        db.rollback()
        raise


def auto_publish_trusted_places(
    db: Session,
    *,
    city_slug: str | None = None,
    limit: int = 500,
    actor: str = "publication_policy",
) -> dict[str, object]:
    query = (
        db.query(Place).join(City, City.id == Place.city_id)
        .filter(Place.publication_status.in_(AUTO_BACKLOG_STATUSES))
    )
    if city_slug:
        query = query.filter(City.slug == city_slug)
    candidates = (
        query.order_by(Place.id.asc()).limit(limit)
        .with_for_update().populate_existing().all()
    )
    published = 0
    skipped = 0
    try:
        for place in candidates:
            if not is_trusted_auto_publish_candidate(place):
                skipped += 1
                continue
            apply_admin_city_publication_place(
                db, place, actor=actor, source="trusted_auto_publish",
                reason="published by trusted source policy", lock_place=False,
            )
            verify_locked_place(
                db, place, actor=actor, reason="trusted source policy",
                action="trusted_auto_publish_verify", verification_status="trusted",
                verification_source=str(place.address_source or place.source or "trusted_source"),
                verification_method="trusted_source_policy",
            )
            audit(db, place, actor, "trusted_auto_publish")
            published += 1
        db.commit()
        return {"published": published, "skipped": skipped, "checked": len(candidates), "limit": limit}
    except Exception:
        db.rollback()
        raise


def is_trusted_auto_publish_candidate(place: Place) -> bool:
    if place.publication_status not in AUTO_BACKLOG_STATUSES or publication_blockers(place):
        return False
    source = str(place.address_source or place.source or "").strip().lower()
    source_is_official = source in OFFICIAL_ADDRESS_SOURCES or "official" in source
    if not place.address or not source_is_official:
        return False
    if float(place.address_confidence or 0) < TRUSTED_ADDRESS_CONFIDENCE:
        return False
    if place.is_spam_poi or place.is_duplicate_suspected or not place.tourist_eligible:
        return False
    return int(place.quality_score or 0) >= TRUSTED_PLACE_QUALITY_SCORE


def reject_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    place = _locked_place(db, place_id)
    if place is None:
        return {"action": "not_found", "place": None}
    try:
        transition_place_publication(
            db, place, to_status="rejected", reason_code=REASON_ADMIN_REJECT,
            actor=actor, source="mobile_review",
            reason_details={"moderation_action": "reject"},
            human_comment="rejected from moderation", lock_place=False,
        )
        audit(db, place, actor, "mobile_review_reject")
        db.commit()
        db.refresh(place)
        return {"action": "rejected", "place": place_payload(db, place)}
    except Exception:
        db.rollback()
        raise


def defer_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    return move_back_to_queue(db, place_id=place_id, actor=actor, action="deferred")


def restore_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    return move_back_to_queue(db, place_id=place_id, actor=actor, action="restored")


def move_back_to_queue(
    db: Session, *, place_id: int, actor: str, action: str
) -> dict[str, object]:
    place = _locked_place(db, place_id)
    if place is None:
        return {"action": "not_found", "place_id": place_id}
    reason_code = REASON_ADMIN_DEFER if action == "deferred" else REASON_NEEDS_MANUAL_REVIEW
    try:
        transition_place_publication(
            db, place, to_status="needs_review", reason_code=reason_code,
            actor=actor, source="mobile_review",
            reason_details={"moderation_action": action},
            human_comment=f"{action} from moderation", lock_place=False,
        )
        audit(db, place, actor, f"mobile_review_{action}")
        db.commit()
        db.refresh(place)
        return {"action": action, "place_id": place.id, "place": place_payload(db, place)}
    except Exception:
        db.rollback()
        raise


def publication_blockers(place: Place) -> list[str]:
    category = (place.canonical_category or place.category or "").strip().lower()
    blockers = []
    if place.status in {"closed", "temporarily_closed", "inactive"} or place.lifecycle_status in {
        "closed", "removed", "inactive",
    }:
        blockers.append("Место закрыто или неактивно")
    if category in NON_ROUTE_CATEGORIES or place.place_layer in NON_ROUTE_LAYERS:
        blockers.append("Категория не подходит для маршрутов")
    if place.lat is None or place.lng is None:
        blockers.append("Нет координат")
    explicit_zero_confidence = place.confidence is not None and float(place.confidence) <= 0
    low_existence_confidence = place.existence_confidence_level == "low"
    if (
        explicit_zero_confidence and low_existence_confidence and not place.address
        and not place.image_url and not place.opening_hours
    ):
        blockers.append("Нулевая уверенность и отсутствуют адрес, фото и часы работы")
    return blockers


def place_payload(db: Session, place: Place) -> dict[str, object]:
    payload = build_place_read(db, place).model_dump(mode="json")
    payload["publication_blockers"] = publication_blockers(place)
    return payload


def audit(db: Session, place: Place, actor: str, action: str) -> None:
    write_system_log(
        db, level="info", module="mobile_review",
        message=f"{action}: {place.title}", details={"action": action},
        city_slug=place.city.slug if place.city else None,
        place_id=place.id, actor_id=actor, commit=False,
    )
