import math

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint

_WALK_METERS_PER_MIN = 75.0
_URBAN_FACTOR = 1.25


def walk_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    meters = _haversine_km(lat1, lng1, lat2, lng2) * 1000.0
    raw = meters / _WALK_METERS_PER_MIN * _URBAN_FACTOR
    return max(1, int(math.ceil(raw)))


def planned_visit_minutes(point: RoutePoint, ctx: MergedContext) -> int:
    visit_minutes = getattr(point, "visit_minutes", None)
    if visit_minutes is not None and visit_minutes > 0:
        return int(visit_minutes)
    base = category_fallback_visit_minutes(getattr(point, "category", None))
    return max(1, int(base * float(ctx.pace_multiplier)))


def category_fallback_visit_minutes(category: str | None) -> int:
    normalized = (category or "").strip().casefold()
    if normalized in ("cafe", "coffee"):
        return 25
    if normalized == "restaurant":
        return 60
    if normalized in ("museum", "gallery"):
        return 90
    if normalized in ("park", "garden"):
        return 45
    if normalized == "viewpoint":
        return 20
    if normalized == "market":
        return 40
    if normalized == "shop":
        return 30
    return 30


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
