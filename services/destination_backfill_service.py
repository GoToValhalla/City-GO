"""Backfill cities and places into destination foundation (idempotent)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.place import Place
from services.destination_bbox import city_bbox_from_model
from services.destination_membership_service import upsert_membership


def backfill_cities_to_destinations(db: Session) -> dict[str, int]:
    stats = {"destinations_created": 0, "scopes_created": 0, "memberships_created": 0, "places_updated": 0}
    cities = db.query(City).order_by(City.id.asc()).all()
    for city in cities:
        dest = _ensure_city_destination(db, city, stats)
        _ensure_default_scope(db, dest, city, stats)
        _backfill_city_places(db, dest, city, stats)
    db.commit()
    return stats


def _ensure_city_destination(db: Session, city: City, stats: dict[str, int]) -> Destination:
    row = db.query(Destination).filter(Destination.legacy_city_id == city.id).first()
    if row is None:
        row = db.query(Destination).filter(Destination.slug == city.slug).first()
    if row is None:
        row = Destination(
            slug=city.slug,
            name=city.name,
            destination_type="city",
            legacy_city_id=city.id,
            center_lat=city.center_lat,
            center_lng=city.center_lng,
            bbox=city.bbox,
            boundary=city.boundary,
            launch_status=city.launch_status,
            is_active=bool(city.is_active),
            is_published=city.launch_status == "published",
            readiness_score=city.readiness_score or 0,
        )
        db.add(row)
        db.flush()
        stats["destinations_created"] += 1
    return row


def _ensure_default_scope(db: Session, dest: Destination, city: City, stats: dict[str, int]) -> None:
    code = "default"
    existing = (
        db.query(DestinationScope)
        .filter(DestinationScope.destination_id == dest.id, DestinationScope.code == code)
        .first()
    )
    if existing is not None:
        return
    scope = DestinationScope(
        destination_id=dest.id,
        code=code,
        name=f"{city.name} — основной контур",
        scope_type="all",
        import_strategy="single_bbox",
        bbox=city_bbox_from_model(city),
        import_profile="tourist_core",
        is_walkable_cluster=dest.destination_type == "city",
        priority=0,
        status="active" if dest.is_published else "draft",
        enabled=True,
    )
    db.add(scope)
    db.flush()
    stats["scopes_created"] += 1


def _backfill_city_places(db: Session, dest: Destination, city: City, stats: dict[str, int]) -> None:
    places = db.query(Place).filter(Place.city_id == city.id).all()
    for place in places:
        existed = (
            db.query(DestinationPlaceMembership.id)
            .filter(
                DestinationPlaceMembership.place_id == place.id,
                DestinationPlaceMembership.destination_id == dest.id,
            )
            .first()
        )
        upsert_membership(
            db,
            place_id=place.id,
            destination_id=dest.id,
            assignment_type="legacy_city",
            is_primary=True,
            confidence=1.0,
            source="backfill",
        )
        if existed is None:
            stats["memberships_created"] += 1
        if place.primary_destination_id != dest.id:
            place.primary_destination_id = dest.id
            stats["places_updated"] += 1
