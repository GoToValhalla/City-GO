"""Настройка import scopes после создания города через админку."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_import_scope import CityImportScope
from schemas.admin import AdminCityCreateRequest
from services.admin_city_bbox import bbox_from_center_radius
from services.admin_city_forward_geocode import geocode_city_name

DEFAULT_SCOPES: tuple[tuple[str, str, str], ...] = (
    ("tourist_core", "tourist_core", "Tourist core"),
    ("food_area", "food_and_coffee", "Food area"),
    ("useful_services", "useful_services", "Useful services"),
)


def finish_city_import_setup(db: Session, city: City, payload: AdminCityCreateRequest, *, now: datetime | None = None) -> City:
    """Геокодинг центра (если нужно) и создание enabled import scopes."""
    current = now or datetime.utcnow()
    lat, lng = _resolve_center(city, payload)
    if lat is None or lng is None:
        return city
    radius_km = float(payload.radius_km or 15)
    bbox = bbox_from_center_radius(lat, lng, radius_km)
    city.center_lat = lat
    city.center_lng = lng
    city.bbox = bbox
    _upsert_default_scopes(db, city_id=city.id, bbox=bbox, now=current)
    db.flush()
    return city


def _resolve_center(city: City, payload: AdminCityCreateRequest) -> tuple[float | None, float | None]:
    if payload.center_lat is not None and payload.center_lng is not None:
        return float(payload.center_lat), float(payload.center_lng)
    if city.center_lat is not None and city.center_lng is not None:
        return float(city.center_lat), float(city.center_lng)
    geo = geocode_city_name(name=payload.name, country=payload.country, region=payload.region)
    if geo is None:
        return None, None
    return geo.lat, geo.lng


def _upsert_default_scopes(db: Session, *, city_id: int, bbox: dict[str, float], now: datetime) -> None:
    for code, profile, title in DEFAULT_SCOPES:
        scope = db.query(CityImportScope).filter_by(city_id=city_id, code=code).first()
        if scope is None:
            scope = CityImportScope(city_id=city_id, code=code, name=title)
            db.add(scope)
        scope.bbox = bbox
        scope.import_profile = profile
        scope.enabled = True
        scope.status = "enabled" if scope.status == "draft" else scope.status
        scope.refresh_interval_hours = scope.refresh_interval_hours or 168
        scope.next_run_at = scope.next_run_at or now
