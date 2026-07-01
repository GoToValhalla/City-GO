from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_read_service import build_place_read
from services.system_log_service import write_system_log

REVIEW_STATUSES = ("draft", "needs_review", "deferred", "unpublished")
NON_ROUTE_CATEGORIES = {"service", "transport", "utility", "pharmacy", "bank", "atm"}
NON_ROUTE_LAYERS = {"service", "transport", "utility"}


def list_review_cities(db: Session) -> dict[str, object]:
    items = []
    for city in db.query(City).order_by(City.name.asc(), City.slug.asc()).all():
        base = db.query(Place).filter(Place.city_id == city.id)
        needs_review = base.filter(Place.publication_status.in_(REVIEW_STATUSES)).count()
        rejected = base.filter(Place.publication_status == "rejected").count()
        published = base.filter(Place.publication_status == "published").count()
        if needs_review or rejected or published or city.launch_status != "draft":
            items.append({"id": city.id, "slug": city.slug, "name": city.name, "needs_review": needs_review, "rejected": rejected, "published": published})
    return {"items": items, "total": len(items)}


def next_review_place(db: Session, city_slug: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return {"city": None, "remaining": 0, "place": None}
    query = db.query(Place).filter(Place.city_id == city.id, Place.is_active.is_(True), Place.publication_status.in_(REVIEW_STATUSES))
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
    now = datetime.utcnow()
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_route_eligible = True
    place.is_searchable = True
    place.publication_status = "published"
    place.publication_comment = "published from mobile review"
    place.published_at = now
    place.unpublished_at = None
    place.verification_status = "verified"
    place.verified_at = now
    place.verified_by = actor
    place.updated_at = now
    db.add(place)
    audit(db, place, actor, "mobile_review_publish")
    db.commit()
    db.refresh(place)
    return {"action": "published", "place": place_payload(db, place)}


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
    place.publication_comment = "rejected from mobile review"
    place.unpublished_at = now
    place.updated_at = now
    db.add(place)
    audit(db, place, actor, "mobile_review_reject")
    db.commit()
    db.refresh(place)
    return {"action": "rejected", "place": place_payload(db, place)}


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
