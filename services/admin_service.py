from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from models.route import Route
from schemas.admin import AdminCityCreateRequest, AdminPlaceCreate, AdminPlaceUpdate
from services.admin_audit_service import write_admin_audit_log
from services.admin_city_import_job_service import queue_city_import_job
from services.admin_city_import_setup import finish_city_import_setup
from services.admin_places_filters import apply_place_filters
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_publication_eligibility import place_publication_eligibility
from services.place_service import create_place, get_place_by_id, update_place
from services.place_verification_mutation import reject_locked_place_verification, verify_locked_place
from services.publication_policy import unsafe_manual_publish_gates
from services.publication_state_writer import (
    REASON_ADMIN_REJECT,
    REASON_ADMIN_UNPUBLISH,
    transition_place_publication,
)
from services.route_service import get_route_by_id


class PlacePublicationBlockedError(ValueError):
    def __init__(self, *, place_id: int, blocked_reason: str, failed_gates: list[str]):
        self.place_id = place_id
        self.blocked_reason = blocked_reason
        self.failed_gates = failed_gates
        super().__init__(f"place {place_id} publish blocked: {blocked_reason}")


def slugify_city_name(name: str) -> str:
    from services.slug_transliterate import transliterate_cyrillic
    latin = transliterate_cyrillic(name.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", latin).strip("-") or "city"


def get_admin_dashboard(db: Session) -> dict[str, int]:
    places_total = db.query(Place).count()
    places_published = db.query(Place).filter(Place.is_published.is_(True)).count()
    return {
        "cities_total": db.query(City).count(),
        "cities_published": db.query(City).filter(City.launch_status == "published", City.is_active.is_(True)).count(),
        "places_total": places_total,
        "places_published": places_published,
        "places_hidden": max(places_total - places_published, 0),
        "places_needs_recheck": db.query(Place).filter(Place.verification_status.in_(("needs_recheck", "unverified"))).count(),
        "places_low_confidence": db.query(Place).filter(Place.existence_confidence_level.in_(("low", "unknown"))).count(),
        "places_without_photo": db.query(Place).filter(Place.image_url.is_(None)).count(),
        "pending_photos": db.query(PlaceImage).filter(PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count(),
        "routes_total": db.query(Route).count(),
        "routes_active": db.query(Route).filter(Route.is_active.is_(True)).count(),
        "audit_events_total": db.query(AdminAuditLog).count(),
    }


def get_admin_places(
    db: Session,
    *,
    city_slug: str | None = None,
    publication_status: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    q: str | None = None,
    preset: str | None = None,
    has_photo: bool | None = None,
    has_address: bool | None = None,
    has_description: bool | None = None,
    route_eligible: bool | None = None,
    low_confidence: bool | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list, int]:
    query = apply_place_filters(
        db, db.query(Place), city_slug=city_slug, publication_status=publication_status,
        verification_status=verification_status, category=category, q=q, preset=preset,
        has_photo=has_photo, has_address=has_address, has_description=has_description,
        route_eligible=route_eligible, low_confidence=low_confidence, source=source,
    )
    total = query.count()
    return query.order_by(Place.updated_at.desc()).offset(offset).limit(limit).all(), total


def create_admin_place(db: Session, payload: AdminPlaceCreate, *, actor: str = "admin") -> Place:
    place = create_place(db, payload)
    write_admin_audit_log(
        db, actor=actor, action="create_place", entity_type="place", entity_id=place.id,
        new_value={"title": place.title, "publication_status": place.publication_status},
    )
    db.commit()
    db.refresh(place)
    return place


def update_admin_place(db: Session, place_id: int, payload: AdminPlaceUpdate, *, actor: str = "admin") -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old_value = {"title": place.title, "status": place.status, "publication_status": place.publication_status}
    place = update_place(db, place_id, payload)
    if place is None:
        return None
    write_admin_audit_log(
        db, actor=actor, action="update_place", entity_type="place", entity_id=place.id,
        old_value=old_value,
        new_value={"title": place.title, "status": place.status, "publication_status": place.publication_status},
    )
    db.commit()
    db.refresh(place)
    return place


def publish_place(db: Session, place_id: int, *, actor: str, reason: str | None = None) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    eligibility = place_publication_eligibility(place)
    failed_gates = list(eligibility.reasons) + unsafe_manual_publish_gates(place)
    if failed_gates:
        raise PlacePublicationBlockedError(
            place_id=place_id, blocked_reason=failed_gates[0], failed_gates=failed_gates
        )
    old_value = _place_publication_snapshot(place)
    apply_admin_city_publication_place(
        db, place, actor=actor, source="admin_place_publish", reason=reason
    )
    write_admin_audit_log(
        db, actor=actor, action="publish_place", entity_type="place", entity_id=place.id,
        old_value=old_value, new_value=_place_publication_snapshot(place), reason=reason,
    )
    db.commit()
    db.refresh(place)
    return place


def unpublish_place(db: Session, place_id: int, *, actor: str, reason: str) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old_value = _place_publication_snapshot(place)
    transition_place_publication(
        db, place, to_status="unpublished", reason_code=REASON_ADMIN_UNPUBLISH,
        actor=actor, source="admin_place_unpublish", human_comment=reason,
    )
    write_admin_audit_log(
        db, actor=actor, action="unpublish_place", entity_type="place", entity_id=place.id,
        old_value=old_value, new_value=_place_publication_snapshot(place), reason=reason,
    )
    db.commit()
    db.refresh(place)
    return place


def reject_place(db: Session, place_id: int, *, actor: str, reason: str) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old_value = _place_publication_snapshot(place)
    old_value["verification_status"] = place.verification_status
    transition_place_publication(
        db, place, to_status="rejected", reason_code=REASON_ADMIN_REJECT,
        actor=actor, source="admin_place_reject", human_comment=reason,
    )
    place.status = "inactive"
    reject_locked_place_verification(
        db, place, actor=actor, reason=reason, action="admin_place_reject_verification"
    )
    new_value = _place_publication_snapshot(place)
    new_value["verification_status"] = place.verification_status
    write_admin_audit_log(
        db, actor=actor, action="reject_place", entity_type="place", entity_id=place.id,
        old_value=old_value, new_value=new_value, reason=reason,
    )
    db.commit()
    db.refresh(place)
    return place


def verify_place(db: Session, place_id: int, *, actor: str, reason: str | None = None) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    verify_locked_place(db, place, actor=actor, reason=reason, action="verify_place")
    db.commit()
    db.refresh(place)
    return place


def create_city_and_queue_import(db: Session, payload: AdminCityCreateRequest, *, actor: str = "admin") -> City:
    base_slug = slugify_city_name(payload.name)
    slug = base_slug
    index = 2
    while db.query(City).filter(City.slug == slug).first() is not None:
        slug = f"{base_slug}-{index}"
        index += 1
    city = City(
        name=payload.name.strip(), slug=slug, country=payload.country,
        region=payload.region, timezone=payload.timezone,
        center_lat=payload.center_lat, center_lng=payload.center_lng,
        launch_status="importing", is_active=False,
    )
    db.add(city)
    db.flush()
    finish_city_import_setup(db, city, payload)
    queue_city_import_job(db, city_id=city.id)
    write_admin_audit_log(
        db, actor=actor, action="create_city_import_request", entity_type="city",
        entity_id=city.id,
        new_value={"name": city.name, "slug": city.slug, "launch_status": city.launch_status, "radius_km": payload.radius_km},
        reason="Создан город и поставлена задача на автоматический сбор мест и фото.",
    )
    db.commit()
    db.refresh(city)
    return city


def get_admin_routes(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[Route], int]:
    query = db.query(Route)
    total = query.count()
    return query.order_by(Route.updated_at.desc()).offset(offset).limit(limit).all(), total


def publish_route(db: Session, route_id: int, *, actor: str, reason: str | None = None) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"is_active": route.is_active}
    route.is_active = True
    write_admin_audit_log(
        db, actor=actor, action="publish_route", entity_type="route", entity_id=route.id,
        old_value=old_value, new_value={"is_active": True}, reason=reason,
    )
    db.commit()
    db.refresh(route)
    return route


def unpublish_route(db: Session, route_id: int, *, actor: str, reason: str) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"is_active": route.is_active}
    route.is_active = False
    write_admin_audit_log(
        db, actor=actor, action="unpublish_route", entity_type="route", entity_id=route.id,
        old_value=old_value, new_value={"is_active": False}, reason=reason,
    )
    db.commit()
    db.refresh(route)
    return route


def _place_publication_snapshot(place: Place) -> dict[str, object]:
    return {
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_route_eligible": place.is_route_eligible,
        "route_exclusion_reason": place.route_exclusion_reason,
        "is_searchable": place.is_searchable,
        "publication_status": place.publication_status,
        "publication_reason_code": place.publication_reason_code,
    }
