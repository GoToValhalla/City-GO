from __future__ import annotations

from services.route_assembly_service import RoutePoint
from services.route_diversity_policy import category_distribution


def total_walk_minutes(route: list[RoutePoint]) -> int:
    return sum(map(_walk_minutes, route))


def time_breakdown(route: list[RoutePoint], budget_minutes: int) -> dict[str, float]:
    visit = sum(map(_visit_minutes, route))
    walk = total_walk_minutes(route)
    total = visit + walk
    utilization = total / budget_minutes if budget_minutes > 0 else 0.0
    return {
        "visit_time_minutes": float(visit),
        "walk_time_minutes": float(walk),
        "total_time_minutes": float(total),
        "budget_utilization": round(max(0.0, min(1.0, utilization)), 3),
    }


def route_category_distribution(route: list[RoutePoint]) -> dict[str, int]:
    return category_distribution(list(route))


def _walk_minutes(point: RoutePoint) -> int:
    return int(getattr(point, "estimated_walk_minutes", 0) or 0)


def _visit_minutes(point: RoutePoint) -> int:
    return int(getattr(point, "visit_minutes", 0) or 0)
