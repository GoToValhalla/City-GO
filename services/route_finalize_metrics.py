from __future__ import annotations

from datetime import datetime
from functools import reduce
from typing import List

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint


def compute_total_time(route: List[RoutePoint]) -> int:
    return sum(int(getattr(point, "visit_minutes", 0) or 0) for point in route)


def compute_distance(route: List[RoutePoint], ctx: MergedContext) -> float:
    points = [(point.lat, point.lng) for point in route]
    start = (0.0, ctx.location)

    def add_distance(state: tuple[float, tuple[float, float]], point: tuple[float, float]):
        total, previous = state
        return (total + distance(previous[0], previous[1], point[0], point[1]), point)

    total, _previous = reduce(add_distance, points, start)
    return round(total, 3)


def point_arrival(point: RoutePoint) -> datetime | None:
    return getattr(point, "estimated_arrival_time", None) or getattr(point, "arrival_time", None)


def point_departure(point: RoutePoint) -> datetime | None:
    return getattr(point, "estimated_departure_time", None) or getattr(point, "departure_time", None)


def compute_time_aware_span(route: List[RoutePoint]) -> tuple[int, datetime | None]:
    first_arrival = point_arrival(route[0])
    last_departure = point_departure(route[-1])

    if first_arrival is not None and last_departure is not None:
        delta = last_departure - first_arrival
        return int(max(0, round(delta.total_seconds() / 60.0))), last_departure

    walk_sum = sum(int(getattr(point, "estimated_walk_minutes", 0) or 0) for point in route)
    visit_sum = compute_total_time(route)
    return max(0, walk_sum + visit_sum), last_departure


def distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return ((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) ** 0.5
