"""Фильтры мест по city-level feature toggles."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place
from services.feature_toggle_service import is_toggle_enabled


def apply_city_quality_filters(query: Query, db: object, *, city_slug: str) -> Query:
    if is_toggle_enabled(db, "verified_places_only", scope="city", scope_id=city_slug, default=False):  # type: ignore[arg-type]
        query = query.filter(Place.verification_status == "verified")
    if is_toggle_enabled(db, "hide_without_photo", scope="city", scope_id=city_slug, default=False):  # type: ignore[arg-type]
        query = query.filter(Place.image_url.isnot(None))
    if is_toggle_enabled(db, "hide_without_address", scope="city", scope_id=city_slug, default=False):  # type: ignore[arg-type]
        query = query.filter(Place.address.isnot(None), Place.address != "")
    if is_toggle_enabled(db, "hide_low_quality", scope="city", scope_id=city_slug, default=False):  # type: ignore[arg-type]
        query = query.filter(Place.existence_confidence_level.notin_(("low", "unknown")))
    return query
