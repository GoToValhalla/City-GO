from __future__ import annotations

from models.route_draft import RouteDraft, RouteDraftPoint
from services.route_geometry import walk_minutes_between


def recalculate_draft(draft: RouteDraft) -> RouteDraft:
    points = sorted(draft.points, key=lambda item: item.position)
    _reindex(points)
    total = _walk_from_start(draft, points) + sum(int(point.visit_minutes or 0) for point in points)
    draft.total_minutes = int(total)
    if not points:
        draft.route_status = "no_route"
    elif total > draft.budget_minutes or len(points) < 2:
        draft.route_status = "partial"
    else:
        draft.route_status = "full"
    return draft


def _reindex(points: list[RouteDraftPoint]) -> None:
    for index, point in enumerate(points, start=1):
        point.position = index
        point.walk_minutes_from_prev = _walk_from_prev(points, index - 1)
        point.walk_minutes_to_next = _walk_to_next(points, index - 1)


def _walk_from_start(draft: RouteDraft, points: list[RouteDraftPoint]) -> int:
    if not points or draft.start_lat is None or draft.start_lng is None:
        return 0
    first = points[0].place
    return walk_minutes_between(float(draft.start_lat), float(draft.start_lng), float(first.lat), float(first.lng))


def _walk_from_prev(points: list[RouteDraftPoint], index: int) -> int | None:
    if index <= 0:
        return None
    prev_place = points[index - 1].place
    place = points[index].place
    return walk_minutes_between(float(prev_place.lat), float(prev_place.lng), float(place.lat), float(place.lng))


def _walk_to_next(points: list[RouteDraftPoint], index: int) -> int | None:
    if index >= len(points) - 1:
        return None
    place = points[index].place
    next_place = points[index + 1].place
    return walk_minutes_between(float(place.lat), float(place.lng), float(next_place.lat), float(next_place.lng))
