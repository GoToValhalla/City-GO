from __future__ import annotations


def shorten_target_place_id(route: object) -> str | None:
    points = list(getattr(route, "points", []) or [])
    return min(points, key=_point_value_per_minute).place_id if points else None


def route_place_ids(route: object) -> set[str]:
    return {str(getattr(point, "place_id", "")) for point in getattr(route, "points", []) or []}


def correction_excluded_ids(route: object, target_place_id: str | None) -> set[str]:
    current = route_place_ids(route)
    return current | ({str(target_place_id)} if target_place_id else set())


def same_category(place: object | None) -> str | None:
    category = getattr(place, "category", None) if place is not None else None
    return category if isinstance(category, str) and category else None


def _point_value_per_minute(point: object) -> float:
    score = _point_score(point)
    minutes = _point_minutes(point)
    return score / max(1, minutes)


def _point_score(point: object) -> float:
    breakdown = getattr(point, "scoring_breakdown", None)
    if isinstance(breakdown, dict) and breakdown:
        return sum(float(value or 0.0) for value in breakdown.values()) / len(breakdown)
    return 0.5


def _point_minutes(point: object) -> int:
    visit = int(getattr(point, "visit_minutes", 0) or 0)
    walk = int(getattr(point, "estimated_walk_minutes", 0) or 0)
    return visit + walk
