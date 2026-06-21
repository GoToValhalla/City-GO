from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint
from services.route_geometry import walk_minutes_between


def walk_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    return walk_minutes_between(lat1, lng1, lat2, lng2)


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
