from __future__ import annotations

import re
from datetime import datetime

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
from services.place_read_service import build_place_read
from services.place_service import create_place, get_place_by_id, get_places, get_places_total, update_place
from services.route_service import get_route_by_id


def slugify_city_name(name: str) -> str:
    from services.slug_transliterate import transliterate_cyrillic

    latin = transliterate_cyrillic(name.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")
    return slug or "city"


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
    items = query.order_by(Place.updated_at.desc()).offset(offset).limit(limit).all()
    return items, total


def create_admin_place(db: Session, payload: AdminPlaceCreate, *, actor: str = "admin") -> Place:
    place = create_place(db, payload)
    write_admin_audit_log(
        db,
        actor=actor,
        action="create_place",
        entity_type="place",
        entity_id=place.id,
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
        db,
        actor=actor,
        action="update_place",
        entity_type="place",
        entity_id=place.id,
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
    old_value = _place_publication_snapshot(place)
    now = datetime.utcnow()
    place.is_active = True
    place.status = "active"
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.is_route_eligible = True
    place.publication_status = "published"
    place.publication_comment = reason
    place.published_at = now
    place.unpublished_at = None
    write_admin_audit_log(
        db,
        actor=actor,
        action="publish_place",
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value=_place_publication_snapshot(place),
        reason=reason,
    )
    db.commit()
    db.refresh(place)
    return place


def unpublish_place(db: Session, place_id: int, *, actor: str, reason: str) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old_value = _place_publication_snapshot(place)
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "unpublished"
    place.publication_comment = reason
    place.unpublished_at = datetime.utcnow()
    write_admin_audit_log(
        db,
        actor=actor,
        action="unpublish_place",
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value=_place_publication_snapshot(place),
        reason=reason,
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
    place.is_active = False
    place.status = "inactive"
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "rejected"
    place.publication_comment = reason
    place.verification_status = "rejected"
    place.verification_comment = reason
    place.unpublished_at = datetime.utcnow()
    new_value = _place_publication_snapshot(place)
    new_value["verification_status"] = place.verification_status
    write_admin_audit_log(
        db,
        actor=actor,
        action="reject_place",
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.commit()
    db.refresh(place)
    return place


def verify_place(db: Session, place_id: int, *, actor: str, reason: str | None = None) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old_value = {"verification_status": place.verification_status, "existence_confidence_level": place.existence_confidence_level}
    place.verification_status = "verified"
    place.existence_confidence_level = "high"
    place.existence_confidence_score = max(place.existence_confidence_score or 0, 90)
    place.verified_by = actor
    place.verified_at = datetime.utcnow()
    place.verification_comment = reason
    write_admin_audit_log(
        db,
        actor=actor,
        action="verify_place",
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value={"verification_status": place.verification_status, "existence_confidence_level": place.existence_confidence_level},
        reason=reason,
    )
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
        name=payload.name.strip(),
        slug=slug,
        country=payload.country,
        region=payload.region,
        timezone=payload.timezone,
        center_lat=payload.center_lat,
        center_lng=payload.center_lng,
        launch_status="importing",
        is_active=False,
    )
    db.add(city)
    db.flush()
    finish_city_import_setup(db, city, payload)
    queue_city_import_job(db, city_id=city.id)
    # payload.actor игнорируется — используем actor из auth context (P0-3)
    write_admin_audit_log(
        db,
        actor=actor,
        action="create_city_import_request",
        entity_type="city",
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
    items = query.order_by(Route.updated_at.desc()).offset(offset).limit(limit).all()
    return items, total


def publish_route(db: Session, route_id: int, *, actor: str, reason: str | None = None) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"is_active": route.is_active}
    route.is_active = True
    write_admin_audit_log(db, actor=actor, action="publish_route", entity_type="route", entity_id=route.id, old_value=old_value, new_value={"is_active": True}, reason=reason)
    db.commit()
    db.refresh(route)
    return route


def unpublish_route(db: Session, route_id: int, *, actor: str, reason: str) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"is_active": route.is_active}
    route.is_active = False
    write_admin_audit_log(db, actor=actor, action="unpublish_route", entity_type="route", entity_id=route.id, old_value=old_value, new_value={"is_active": False}, reason=reason)
    db.commit()
    db.refresh(route)
    return route


def _place_publication_snapshot(place: Place) -> dict[str, object]:
    return {
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_route_eligible": place.is_route_eligible,
        "is_searchable": place.is_searchable,
        "publication_status": place.publication_status,
    }