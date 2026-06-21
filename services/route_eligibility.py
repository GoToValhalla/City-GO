from __future__ import annotations

from typing import Any

from models.place import Place
from services.place_public_visibility import public_route_place_conditions


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """SQL visibility contract for places that may enter route retrieval."""
    return (
        *public_route_place_conditions(),
        Place.lat.is_not(None),
        Place.lng.is_not(None),
    )
