from __future__ import annotations

from typing import Any

from sqlalchemy import func

from models.place import Place
from services.place_public_visibility import (\n    admin_preview_route_place_conditions,\n    public_route_place_conditions,\n)


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """SQL visibility contract for user-facing route retrieval."""

    return _route_eligible_conditions(public_route_place_conditions())


def admin_preview_route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Route gates for an authenticated admin preview of an unpublished city."""

    return _route_eligible_conditions(admin_preview_route_place_conditions())


def _route_eligible_conditions(place_conditions: tuple[Any, ...]) -> tuple[Any, ...]:
    return (
        *place_conditions,
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        # Import placeholders such as "Место для прогулки OSM 1971922" are
        # unresolved source records, not names suitable for a user route.
        ~func.lower(Place.title).like("% osm %"),
    )