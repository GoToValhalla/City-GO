from __future__ import annotations

from services.route_geometry import walk_minutes_between


def annotate_walks(route: list[object], start: tuple[float, float]) -> list[object]:
    return _annotate(route, start[0], start[1])


def _annotate(route: list[object], lat: float, lng: float) -> list[object]:
    if not route:
        return []
    first, *tail = route
    first.estimated_walk_minutes = walk_minutes_between(lat, lng, first.lat, first.lng)
    return [first, *_annotate(tail, first.lat, first.lng)]
