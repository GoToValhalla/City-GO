"""BBox вокруг центра города для import scopes."""

from __future__ import annotations

import math
from typing import TypedDict


class CityBbox(TypedDict):
    south: float
    west: float
    north: float
    east: float


def bbox_from_center_radius(lat: float, lng: float, radius_km: float) -> CityBbox:
    """Квадратный bbox по радиусу сбора (км) от центра."""
    safe_radius = max(float(radius_km), 1.0)
    delta_lat = safe_radius / 111.0
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    delta_lng = safe_radius / (111.0 * cos_lat)
    return {
        "south": lat - delta_lat,
        "west": lng - delta_lng,
        "north": lat + delta_lat,
        "east": lng + delta_lng,
    }
