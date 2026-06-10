from __future__ import annotations


def route_place_ids(route: dict[str, object]) -> list[str]:
    return [
        str(point.get("place_id"))
        for point in _points(route)
        if point.get("place_id") is not None
    ]


def first_route_place_id(route: dict[str, object]) -> str | None:
    points = _points(route)
    if not points:
        return None
    raw = points[0].get("place_id")
    return str(raw) if raw is not None else None


def shortened_time_budget(route: dict[str, object]) -> int:
    context = route.get("context")
    raw = context.get("time_budget_minutes") if isinstance(context, dict) else None
    current = int(raw) if isinstance(raw, int) else 120
    return max(30, current - 30)


def _points(route: dict[str, object]) -> list[dict[str, object]]:
    raw = route.get("points")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]
