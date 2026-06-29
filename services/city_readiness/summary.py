"""Сводка readiness по всем городам."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.data_foundation import CityQualitySnapshot
from services.city_readiness.score import latest_city_readiness_snapshot


def city_readiness_snapshot(db: Session, *, city_slug: str) -> dict[str, object] | None:
    """Return the last persisted readiness snapshot without live recomputation."""
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    snapshot = latest_city_readiness_snapshot(db, city_slug=city_slug)
    if snapshot is not None:
        return _snapshot_payload(city, snapshot)
    return _city_fallback_payload(city)


def list_cities_readiness(db: Session, *, limit: int = 100) -> list[dict[str, object]]:
    cities = db.query(City).order_by(City.name.asc()).limit(limit).all()
    return [city_readiness_snapshot(db, city_slug=city.slug) or _city_fallback_payload(city) for city in cities]


def _snapshot_payload(city: City, snapshot: CityQualitySnapshot) -> dict[str, object]:
    if isinstance(snapshot.snapshot_payload, dict):
        payload = dict(snapshot.snapshot_payload)
        payload.setdefault("city_slug", city.slug)
        payload.setdefault("city_name", city.name)
        payload.setdefault("readiness_score", snapshot.readiness_score)
        payload.setdefault("status", snapshot.quality_status)
        payload.setdefault("components", _components_from_snapshot(snapshot))
        payload.pop("data_quality_diagnostics", None)
        return payload
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": snapshot.readiness_score,
        "status": snapshot.quality_status,
        "components": _components_from_snapshot(snapshot),
    }


def _city_fallback_payload(city: City) -> dict[str, object]:
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": int(city.readiness_score or 0),
        "status": city.quality_status or city.launch_status or "unknown",
        "components": {
            "places_total": 0,
            "places_active": 0,
            "eligible_places": 0,
        },
    }


def _components_from_snapshot(snapshot: CityQualitySnapshot) -> dict[str, float | int]:
    return {
        "places_total": snapshot.total_places_imported,
        "places_active": snapshot.total_places_active,
        "eligible_places": snapshot.total_places_route_eligible,
        "spam_poi_count": snapshot.spam_poi_count,
        "spam_poi_pct": snapshot.spam_poi_pct,
        "photo_coverage_pct": snapshot.photo_coverage_pct,
        "any_photo_pct": snapshot.any_photo_pct,
        "address_full_pct": snapshot.address_full_pct,
        "address_any_pct": snapshot.address_any_pct,
        "description_any_pct": snapshot.description_any_pct,
        "hours_any_pct": snapshot.hours_any_pct,
        "gold_pct": snapshot.gold_pct,
        "silver_pct": snapshot.silver_pct,
        "bronze_pct": snapshot.bronze_pct,
        "draft_pct": snapshot.draft_pct,
        "rejected_pct": snapshot.rejected_pct,
        "stale_places_pct": snapshot.stale_places_pct,
        "never_verified_pct": snapshot.never_verified_pct,
    }
