from __future__ import annotations

import math


WALK_METERS_PER_MIN = 75.0
URBAN_FACTOR = 1.25


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return _haversine_km(lat1, lng1, lat2, lng2) * 1000.0


def walk_minutes_between(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    raw = distance_meters(lat1, lng1, lat2, lng2) / WALK_METERS_PER_MIN * URBAN_FACTOR
    return max(1, int(math.ceil(raw)))


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
