import math
from datetime import datetime
from typing import Sequence

from schemas.merged_context import MergedContext
from services.itinerary_time_service import resolve_open_windows_for_datetime
from services.route_assembly_service import RoutePoint
from services.route_start_time import effective_route_start
from services.route_timezone import ensure_local_datetime, local_now

_CLOSING_SOON_MINUTES = 90
_MAX_FORCE_DISTANCE_KM = 3.0


class RouteTimeOrderingService:
    def order(
        self,
        route: Sequence[RoutePoint],
        ctx: MergedContext,
        start_time: datetime,
    ) -> list[RoutePoint]:
        route_start = _route_start(ctx, start_time)
        indexed = tuple(enumerate(route))
        return list(map(_point, sorted(indexed, key=lambda item: _priority(item, ctx, route_start))))


def _route_start(ctx: MergedContext, start_time: datetime) -> datetime:
    if getattr(ctx, "time_of_day", None):
        return effective_route_start(local_now(ctx), getattr(ctx, "time_of_day", None))
    return ensure_local_datetime(start_time, ctx)


def _priority(
    item: tuple[int, RoutePoint],
    ctx: MergedContext,
    start_time: datetime,
) -> tuple[int, int, int]:
    index, point = item
    close_minutes = _close_minutes(point, start_time)
    urgent = _is_urgent(point, ctx, close_minutes)
    return (0 if urgent else 1, close_minutes if urgent else 9999, index)


def _is_urgent(point: RoutePoint, ctx: MergedContext, close_minutes: int) -> bool:
    return (
        0 <= close_minutes <= _CLOSING_SOON_MINUTES
        and _distance_from_start_km(point, ctx) <= _MAX_FORCE_DISTANCE_KM
    )


def _close_minutes(point: RoutePoint, start_time: datetime) -> int:
    opening_hours = getattr(point, "opening_hours", None)
    if not isinstance(opening_hours, dict) or not opening_hours:
        return 9999
    windows = resolve_open_windows_for_datetime(opening_hours, start_time)
    current = tuple(filter(lambda window: window[0] <= start_time <= window[1], windows))
    if not current:
        return 9999
    close_dt = min(map(lambda window: window[1], current))
    return int((close_dt - start_time).total_seconds() // 60)


def _distance_from_start_km(point: RoutePoint, ctx: MergedContext) -> float:
    start_lat, start_lng = ctx.location
    return _haversine_km(start_lat, start_lng, point.lat, point.lng)


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


def _point(item: tuple[int, RoutePoint]) -> RoutePoint:
    return item[1]