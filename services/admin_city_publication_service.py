from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.place_public_visibility import is_public_hidden_category

CITY_STATUS_DRAFT = "draft"
CITY_STATUS_PUBLISHED = "published"
CITY_STATUS_REVIEW_REQUIRED = "review_required"
CITY_STATUS_UNPUBLISHED = "unpublished"

PLACE_STATUS_ACTIVE = "active"
PLACE_PUBLICATION_PUBLISHED = "published"
PLACE_PUBLICATION_NEEDS_REVIEW = "needs_review"
PLACE_PUBLICATION_UNPUBLISHED = "unpublished"


@dataclass(frozen=True)
class CityPublicationResult:
    city: City
    places_total: int
    places_published: int
    places_hidden: int


def publish_city(db: Session, city_id: int, *, actor: str, reason: str | None = None) -> CityPublicationResult | None:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None

    places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
    now = datetime.utcnow()
    old_value = _city_publication_snapshot(city)
    published_count = 0
    hidden_count = 0

    for place in places:
        if _place_can_be_public(place):
            _publish_place_for_city(place, now=now, reason=reason)
            published_count += 1
        else:
            _hide_place_for_city_publication(place, now=now, reason="city_publication_quality_gate")
            hidden_count += 1

    if published_count <= 0:
        db.rollback()
        raise ValueError("Нельзя опубликовать город: нет ни одного места, прошедшего публичный quality gate.")

    city.launch_status = CITY_STATUS_PUBLISHED
    city.is_active = True
    city.last_import_at = city.last_import_at or now
    city.updated_at = now

    write_admin_audit_log(
        db,
        actor=actor,
        action="publish_city",
        entity_type="city",
        entity_id=city.id,
        old_value=old_value,
        new_value={
            **_city_publication_snapshot(city),
            "places_total": len(places),
            "places_published": published_count,
            "places_hidden": hidden_count,
        },
        reason=reason,
    )
    db.commit()
    db.refresh(city)
    return CityPublicationResult(
        city=city,
        places_total=len(places),
        places_published=published_count,
        places_hidden=hidden_count,
    )


def unpublish_city(db: Session, city_id: int, *, actor: str, reason: str) -> CityPublicationResult | None:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None

    places = db.query(Place).filter(Place.city_id == city.id).all()
    now = datetime.utcnow()
    old_value = _city_publication_snapshot(city)

    for place in places:
        place.is_published = False
        place.is_visible_in_catalog = False
        place.is_searchable = False
        place.is_route_eligible = False
        place.publication_status = PLACE_PUBLICATION_UNPUBLISHED
        place.publication_comment = reason
        place.unpublished_at = now
        place.updated_at = now

    city.launch_status = CITY_STATUS_UNPUBLISHED
    city.is_active = False
    city.updated_at = now

    write_admin_audit_log(
        db,
        actor=actor,
        action="unpublish_city",
        entity_type="city",
        entity_id=city.id,
        old_value=old_value,
        new_value={
            **_city_publication_snapshot(city),
            "places_total": len(places),
            "places_published": 0,
            "places_hidden": len(places),
        },
        reason=reason,
    )
    db.commit()
    db.refresh(city)
    return CityPublicationResult(
        city=city,
        places_total=len(places),
        places_published=0,
        places_hidden=len(places),
    )


def _place_can_be_public(place: Place) -> bool:
    if not place.is_active:
        return False
    if place.status not in {None, PLACE_STATUS_ACTIVE}:
        return False
    if is_public_hidden_category(place.category):
        return False
    if bool(getattr(place, "is_spam_poi", False)):
        return False
    if bool(getattr(place, "is_duplicate_suspected", False)):
        return False
    if place.lat is None or place.lng is None:
        return False
    if _is_blank(place.title):
        return False
    return True


def _publish_place_for_city(place: Place, *, now: datetime, reason: str | None) -> None:
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.is_route_eligible = True
    place.publication_status = PLACE_PUBLICATION_PUBLISHED
    place.publication_comment = reason
    place.published_at = now
    place.unpublished_at = None
    place.updated_at = now


def _hide_place_for_city_publication(place: Place, *, now: datetime, reason: str) -> None:
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    if place.publication_status == PLACE_PUBLICATION_PUBLISHED:
        place.publication_status = PLACE_PUBLICATION_NEEDS_REVIEW
    elif not place.publication_status:
        place.publication_status = PLACE_PUBLICATION_NEEDS_REVIEW
    place.publication_comment = reason
    place.unpublished_at = now
    place.updated_at = now


def _city_publication_snapshot(city: City) -> dict[str, object]:
    return {
        "slug": city.slug,
        "launch_status": city.launch_status,
        "is_active": city.is_active,
        "readiness_score": city.readiness_score,
        "quality_status": city.quality_status,
    }


def _is_blank(value: str | None) -> bool:
    return not bool(str(value or "").strip())