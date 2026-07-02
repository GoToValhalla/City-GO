from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_read_service import build_place_read
from services.system_log_service import write_system_log

MANUAL_REVIEW_STATUSES = ("needs_review", "deferred", "unpublished")
AUTO_BACKLOG_STATUSES = ("draft",)
NON_ROUTE_CATEGORIES = {"service", "transport", "utility", "pharmacy", "bank", "atm"}
NON_ROUTE_LAYERS = {"service", "transport", "utility"}
TRUSTED_ADDRESS_CONFIDENCE = 0.85
TRUSTED_PLACE_QUALITY_SCORE = 65
OFFICIAL_ADDRESS_SOURCES = {"official", "official_site", "official_website", "website", "site", "business_site"}


def list_review_cities(db: Session) -> dict[str, object]:
    cities = db.query(City).order_by(City.name.asc(), City.slug.asc()).all()
    counts = _publication_counts(db, [int(city.id) for city in cities])
    items = []
    for city in cities:
        city_counts = counts.get(int(city.id), {})
        needs_review = sum(int(city_counts.get(status, 0)) for status in MANUAL_REVIEW_STATUSES)
        rejected = int(city_counts.get("rejected", 0))
        auto_backlog = sum(int(city_counts.get(status, 0)) for status in AUTO_BACKLOG_STATUSES)
        if needs_review or rejected:
            items.append(
                {
                    "id": city.id,
                    "slug": city.slug,
                    "name": city.name,
                    "needs_review": needs_review,
                    "rejected": rejected,
                    "auto_backlog": auto_backlog,
                }
            )
    return {"items": items, "total": len(items)}


def _publication_counts(db: Session, city_ids: list[int]) -> dict[int, dict[str, int]]:
    if not city_ids:
        return {}
    rows = (
        db.query(Place.city_id, Place.publication_status, func.count(Place.id))
        .filter(Place.city_id.in_(city_ids))
        .group_by(Place.city_id, Place.publication_status)
        .all()
    )
    result: dict[int, dict[str, int]] = {}
    for city_id, status, count in rows:
        result.setdefault(int(city_id), {})[str(status or "unknown")] = int(count or 0)
    return result


def next_review_place(db: Session, city_slug: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return {"city": None, "remaining": 0, "place": None}
    query = db.query(Place).filter(Place.city_id == city.id, Place.publication_status.in_(MANUAL_REVIEW_STATUSES))
    total = query.count()
    place = query.order_by(Place.updated_at.asc(), Place.id.asc()).first()
    return {"city": {"id": city.id, "slug": city.slug, "name": city.name}, "remaining": total, "place": place_payload(db, place) if place else None}


def rejected_places(db: Session, city_slug: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return {"items": [], "total": 0, "city": None}
    items = db.query(Place).filter(Place.city_id == city.id, Place.publication_status == "rejected").order_by(Place.updated_at.desc(), Place.id.desc()).limit(100).all()
    return {"items": [place_payload(db, item) for item in items], "total": len(items), "city": {"id": city.id, "slug": city.slug, "name": city.name}}


def publish_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        return {"action": "not_found", "place": None}
    blockers = publication_blockers(place)
    if blockers:
        raise HTTPException(422, "; ".join(blockers))
    _publish_place(place, actor, comment="published from moderation")
    db.add(place)
    audit(db, place, actor, "mobile_review_publish")
    db.commit()
    db.refresh(place)
    return {"action": "published", "place": place_payload(db, place)}


def auto_publish_trusted_places(db: Session, *, city_slug: str | None = None, limit: int = 500, actor: str = "publication_policy") -> dict[str, object]:
    query = db.query(Place).join(City, City.id == Place.city_id).filter(Place.publication_status.in_(AUTO_BACKLOG_STATUSES))
    if city_slug:
        query = query.filter(City.slug == city_slug)
    candidates = query.order_by(Place.updated_at.asc(), Place.id.asc()).limit(limit).all()
    published = 0
    skipped = 0
    for place in candidates:
        if is_trusted_auto_publish_candidate(place):
            _publish_place(place, actor, comment="published by trusted source policy")
            audit(db, place, actor, "trusted_auto_publish")
            db.add(place)
            published += 1
        else:
            skipped += 1
    db.commit()
    return {"published": published, "skipped": skipped, "checked": len(candidates), "limit": limit}


def is_trusted_auto_publish_candidate(place: Place) -> bool:
    if place.publication_status not in AUTO_BACKLOG_STATUSES:
        return False
    if publication_blockers(place):
        return False
    source = str(place.address_source or place.source or "").strip().lower()
    source_is_official = source in OFFICIAL_ADDRESS_SOURCES or "official" in source
    address_confidence = float(place.address_confidence or 0)
    if not place.address or not source_is_official or address_confidence < TRUSTED_ADDRESS_CONFIDENCE:
        return False
    if place.is_spam_poi or place.is_duplicate_suspected:
        return False
    if not place.tourist_eligible:
        return False
    if int(place.quality_score or 0) < TRUSTED_PLACE_QUALITY_SCORE:
        return False
    return True


def _publish_place(place: Place, actor: str, *, comment: str) -> None:
    now = datetime.utcnow()
    place.is_active = True
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_route_eligible = True
    place.is_searchable = True
    place.publication_status = "published"
    place.publication_comment = comment
    place.published_at = now
    place.unpublished_at = None
    place.verification_status = "verified"
    place.verified_at = now
    place.verified_by = actor
    place.updated_at = now


def reject_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        return {"action": "not_found", "place": None}
    now = datetime.utcnow()
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_route_eligible = False
    place.is_searchable = False
    place.publication_status = "rejected"
    place.publication_comment = "rejected from moderation"
    place.unpublished_at = now
    place.updated_at = now
    db.add(place)
    audit(db, place, actor, "mobile_review_reject")
    db.commit()
    db.refresh(place)
    return {"action": "rejected", "place": place_payload(db, place)}


def defer_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    return move_back_to_queue(db, place_id=place_id, actor=actor, action="deferred")


def restore_place(db: Session, place_id: int, actor: str) -> dict[str, object]:
    return move_back_to_queue(db, place_id=place_id, actor=actor, action="restored")


def move_back_to_queue(db: Session, *, place_id: int, actor: str, action: str) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        return {"action": "not_found", "place_id": place_id}
    now = datetime.utcnow()
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_route_eligible = False
    place.is_searchable = False
    place.publication_status = "needs_review"
    place.publication_comment = f"{action} from moderation"
    place.updated_at = now
    db.add(place)
    audit(db, place, actor, f"mobile_review_{action}")
    db.commit()
    db.refresh(place)
    return {"action": action, "place_id": place.id, "place": place_payload(db, place)}


def publication_blockers(place: Place) -> list[str]:
    category = (place.canonical_category or place.category or "").strip().lower()
    blockers = []
    if place.status in {"closed", "temporarily_closed", "inactive"} or place.lifecycle_status in {"closed", "removed", "inactive"}:
        blockers.append("Место закрыто или неактивно")
    if category in NON_ROUTE_CATEGORIES or place.place_layer in NON_ROUTE_LAYERS:
        blockers.append("Категория не подходит для маршрутов")
    if place.lat is None or place.lng is None:
        blockers.append("Нет координат")
    return blockers


def place_payload(db: Session, place: Place) -> dict[str, object]:
    payload = build_place_read(db, place).model_dump(mode="json")
    payload["publication_blockers"] = publication_blockers(place)
    return payload


def audit(db: Session, place: Place, actor: str, action: str) -> None:
    write_system_log(db, level="info", module="mobile_review", message=f"{action}: {place.title}", details={"action": action}, city_slug=place.city.slug if place.city else None, place_id=place.id, actor_id=actor, commit=False)
