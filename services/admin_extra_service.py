from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from models.user_signal import UserSignal
from schemas.user_signal import SIGNAL_ROUTE_FEEDBACK

ADMIN_ROLES = [
    {
        "code": "admin",
        "title": "Администратор",
        "permissions": ["all"],
    },
    {
        "code": "editor",
        "title": "Редактор",
        "permissions": ["places:edit", "places:publish", "routes:edit", "routes:publish", "photos:review"],
    },
    {
        "code": "moderator",
        "title": "Модератор",
        "permissions": ["places:verify", "photos:review", "feedback:view"],
    },
    {
        "code": "viewer",
        "title": "Наблюдатель",
        "permissions": ["read"],
    },
]


def admin_coverage(db: Session, city_id: int) -> dict[str, object] | None:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None
    places = db.query(Place).filter(Place.city_id == city.id)
    categories: dict[str, int] = {}
    for category, count in db.query(Place.category, Place.id).filter(Place.city_id == city.id).all():
        key = category or "unknown"
        categories[key] = categories.get(key, 0) + 1
    total = places.count()
    published = places.filter(Place.is_published.is_(True)).count()
    pending_photos = (
        db.query(PlaceImage)
        .join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
        .count()
    )
    return {
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "places_total": total,
        "places_published": published,
        "places_unpublished": max(total - published, 0),
        "places_without_photo": places.filter(Place.image_url.is_(None)).count(),
        "places_needs_recheck": places.filter(Place.verification_status.in_(("needs_recheck", "unverified"))).count(),
        "pending_photos": pending_photos,
        "route_eligible_places": places.filter(Place.is_route_eligible.is_(True)).count(),
        "categories": categories,
    }


def admin_route_feedback(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(UserSignal).filter(UserSignal.signal_type == SIGNAL_ROUTE_FEEDBACK).order_by(UserSignal.created_at.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return [_feedback_payload(row) for row in rows], total


def _feedback_payload(signal: UserSignal) -> dict[str, object]:
    payload = signal.payload or {}
    return {
        "id": signal.id,
        "user_id": signal.user_id,
        "route_id": signal.entity_id,
        "rating": payload.get("rating"),
        "comment": payload.get("comment"),
        "problem_types": payload.get("problem_types") or [],
        "created_at": signal.created_at,
    }
