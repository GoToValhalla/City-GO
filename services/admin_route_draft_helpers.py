"""Helpers for admin route draft publishing pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.route import Route
from models.route_draft import RouteDraft
from schemas.admin_route_dry_run import AdminRouteDryRunRequest
from services.route_service import build_route_points


def city_or_404(db: Session, city_slug: str) -> City:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return city


def places_by_id(db: Session, place_ids: list[int]) -> dict[int, Place]:
    places = db.query(Place).filter(Place.id.in_(place_ids)).all()
    found = {place.id: place for place in places}
    missing = [place_id for place_id in place_ids if place_id not in found]
    if missing:
        raise HTTPException(status_code=409, detail={"code": "SELECTED_PLACE_NOT_FOUND", "place_ids": missing})
    return found


def unique_route_slug(db: Session, base: str) -> str:
    slug = base.strip().lower().replace(" ", "-")
    counter = 2
    current = slug
    while _slug_taken(db, current):
        current = f"{slug}-{counter}"
        counter += 1
    return current


def route_payload(route: Route) -> dict[str, object]:
    return {
        "id": route.id,
        "city_id": route.city_id,
        "slug": route.slug,
        "title": route.title,
        "short_description": route.short_description,
        "duration_minutes": route.duration_minutes,
        "distance_km": route.distance_km,
        "route_mode": route.route_mode,
        "is_active": route.is_active,
        "created_at": route.created_at,
        "updated_at": route.updated_at,
        "points": build_route_points(route),
    }


def build_admin_draft(city: City, request: AdminRouteDryRunRequest) -> RouteDraft:
    return RouteDraft(
        city_id=city.id,
        start_lat=request.start_lat or city.center_lat,
        start_lng=request.start_lng or city.center_lng,
        start_label="Admin dry-run",
        budget_minutes=request.duration_min,
        random_seed=0,
        selected_category_slugs=request.interests,
        category_mode="admin_dry_run",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


def _slug_taken(db: Session, slug: str) -> bool:
    return db.query(Route.id).filter(Route.slug == slug).first() is not None
