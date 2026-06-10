from __future__ import annotations

from typing import Iterable, List

from services.route_assembly_service import RoutePoint

_VISIT_DURATION_ISSUE_CODES = frozenset(
    {
        "visit_duration_invalid_type",
        "visit_duration_non_positive",
    }
)

_VISIT_DURATION_ROUTE_WARNING = "Для некоторых мест использовано приблизительное время визита."


def time_warned_place_ids(route: List[RoutePoint]) -> List[str]:
    return [
        str(getattr(point, "place_id", ""))
        for point in route
        if _has_time_warning(point)
    ]


def route_level_warning_strings(
    route: List[RoutePoint],
    extra_warnings: Iterable[str] | None = None,
) -> List[str]:
    candidates = [
        _VISIT_DURATION_ROUTE_WARNING
        for _value in [None]
        if _route_has_visit_duration_issue(route)
    ]
    return _unique_non_empty(candidates + list(extra_warnings or []))


def _has_time_warning(point: RoutePoint) -> bool:
    status = getattr(point, "time_status", None)
    return status is not None and status != "ok"


def _route_has_visit_duration_issue(route: List[RoutePoint]) -> bool:
    return any(_has_visit_duration_issue(point) for point in route)


def _has_visit_duration_issue(point: RoutePoint) -> bool:
    raw = getattr(point, "validation", None)
    issues = raw.get("issues") if isinstance(raw, dict) else None
    return isinstance(issues, list) and any(
        isinstance(item, str) and item in _VISIT_DURATION_ISSUE_CODES
        for item in issues
    )


def _unique_non_empty(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
