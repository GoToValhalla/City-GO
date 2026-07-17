from __future__ import annotations

from datetime import datetime
from typing import Any

from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.explainability_service import ExplainabilityService
from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute
from services.route_navigation_service import navigation_payload
from services.route_user_warnings import route_warning_message, user_warnings

UNKNOWN_ADDRESS = "Адрес уточняется"
UNKNOWN_TITLE = "Место без названия"


def final_route_to_state(
    final: FinalRoute,
    intent: UserRouteIntent,
    *,
    revision: int = 1,
    status: str | None = None,
) -> UserRouteState:
    explanation = ExplainabilityService().build_route_explanation(final)
    points = list(getattr(final, "points", []) or [])
    raw_warnings = [str(item) for item in getattr(final, "warnings", []) or []]
    resolved_status = str(status or getattr(final, "status", None) or "ready")
    return UserRouteState(
        route_id=str(final.route_id),
        revision=revision,
        status=resolved_status,
        partial_reason=getattr(final, "partial_reason", None),
        context=intent,
        total_places=int(getattr(final, "total_places", len(points)) or len(points)),
        total_minutes=int(getattr(final, "total_minutes", 0) or 0),
        total_estimated_minutes=int(getattr(final, "total_estimated_minutes", 0) or 0),
        estimated_distance=float(getattr(final, "estimated_distance", 0.0) or 0.0),
        estimated_end_time=_iso_dt(getattr(final, "estimated_end_time", None)),
        has_warnings=bool(getattr(final, "has_warnings", False)),
        warning_count=int(getattr(final, "warning_count", 0) or 0),
        places_with_warnings=list(getattr(final, "places_with_warnings", []) or []),
        quality_score=float(getattr(final, "quality_score", 0.0) or 0.0),
        quality_status=str(getattr(final, "quality_status", None) or _quality_status_from_breakdown(final)),
        quality_breakdown=_safe_dict(getattr(final, "quality_breakdown", {}) or {}),
        total_walk_distance_meters=int(getattr(final, "total_walk_distance_meters", 0) or 0),
        time_breakdown=dict(getattr(final, "time_breakdown", {}) or {}),
        category_distribution=dict(getattr(final, "category_distribution", {}) or {}),
        warnings=[route_warning_message(code) for code in raw_warnings],
        user_warnings=user_warnings(final),
        points=[_point_to_schema(index, point) for index, point in enumerate(points, 1)],
        candidate_options=[_point_to_schema(index, point) for index, point in enumerate(getattr(final, "candidate_options", []) or [], 1)],
        explanation=explanation,
        debug_trace=list(getattr(final, "pipeline_trace", []) or []),
    )


def _point_to_schema(position: int, point: RoutePoint) -> UserRoutePoint:
    lat = _float_or_zero(getattr(point, "lat", 0.0))
    lng = _float_or_zero(getattr(point, "lng", 0.0))
    walk_mins = _optional_int(getattr(point, "estimated_walk_minutes", None))
    address = _text_or_default(getattr(point, "address", None), UNKNOWN_ADDRESS)
    nav = navigation_payload(
        lat=lat,
        lng=lng,
        address=address,
        estimated_walk_minutes=walk_mins,
    )
    return UserRoutePoint(
        place_id=str(getattr(point, "place_id", "")),
        city_slug=getattr(point, "city_slug", None),
        position=position,
        title=_text_or_default(getattr(point, "title", None), UNKNOWN_TITLE),
        address=address,
        image_url=_text_or_none(getattr(point, "image_url", None)),
        short_description=_text_or_none(getattr(point, "short_description", None)),
        source=_text_or_none(getattr(point, "source", None)),
        lat=lat,
        lng=lng,
        category=str(getattr(point, "category", "") or ""),
        visit_minutes=int(getattr(point, "visit_minutes", 0) or 0),
        estimated_walk_minutes=walk_mins,
        estimated_arrival_time=_iso_dt(getattr(point, "estimated_arrival_time", None)),
        estimated_departure_time=_iso_dt(getattr(point, "estimated_departure_time", None)),
        time_status=getattr(point, "time_status", None),
        time_warning=getattr(point, "time_warning", None),
        scoring_breakdown=_safe_dict(getattr(point, "scoring_breakdown", {}) or {}),
        **nav,
    )


def _quality_status_from_breakdown(final: FinalRoute) -> str:
    breakdown = getattr(final, "quality_breakdown", {}) or {}
    status = breakdown.get("status") if isinstance(breakdown, dict) else None
    return str(status or "weak")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso_dt(value: object) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _float_or_zero(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _text_or_default(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _text_or_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _safe_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[str(key)] = item
        else:
            safe[str(key)] = str(item)
    return safe
