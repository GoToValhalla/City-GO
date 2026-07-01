from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_read_service import build_place_read

REVIEW_STATUSES = ("draft", "needs_review", "deferred", "unpublished")


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


def place_payload(db: Session, place: Place) -> dict[str, object]:
    payload = build_place_read(db, place).model_dump(mode="json")
    payload["publication_blockers"] = []
    return payload
