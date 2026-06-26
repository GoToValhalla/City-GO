from __future__ import annotations

from typing import Any

from sqlalchemy import func

from models.place import Place
from services.place_public_visibility import public_route_place_conditions


def route_eligible_sql_conditions(*, require_published_city: bool = True) -> tuple[Any, ...]:
    """SQL visibility contract for places that may enter route retrieval."""
    return (
        *public_route_place_conditions(require_published_city=require_published_city),
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        # Import placeholders such as "Место для прогулки OSM 1971922" are
        # unresolved source records, not names suitable for a user route.
        ~func.lower(Place.title).like("% osm %"),
    )