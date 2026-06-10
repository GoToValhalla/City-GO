from __future__ import annotations

from datetime import datetime

from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.explainability_service import ExplainabilityService
from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute
from services.route_navigation_service import navigation_payload
from services.route_user_warnings import user_warnings


def final_route_to_state(
    final: FinalRoute,
    intent: UserRouteIntent,
    *,
    revision: int = 1,
    status: str = "ready",
) -> UserRouteState:
    explanation = ExplainabilityService().build_route_explanation(final)
    return UserRouteState(
        route_id=str(final.route_id),
        revision=revision,
        status=str(getattr(final, "status", None) or status),
        partial_reason=getattr(final, "partial_reason", None),
        context=intent,
        total_places=int(final.total_places),
        total_minutes=int(final.total_minutes),
        total_estimated_minutes=int(getattr(final, "total_estimated_minutes", 0) or 0),
        estimated_distance=float(final.estimated_distance),
        estimated_end_time=_iso_dt(getattr(final, "estimated_end_time", None)),
        has_warnings=bool(getattr(final, "has_warnings", False)),
        warning_count=int(getattr(final, "warning_count", 0) or 0),
        places_with_warnings=list(getattr(final, "places_with_warnings", []) or []),
        quality_score=float(getattr(final, "quality_score", 0.0) or 0.0),
        quality_status=str(getattr(final, "quality_status", None) or _quality_status_from_breakdown(final)),
        quality_breakdown=dict(getattr(final, "quality_breakdown", {}) or {}),
        total_walk_distance_meters=int(getattr(final, "total_walk_distance_meters", 0) or 0),
        time_breakdown=dict(getattr(final, "time_breakdown", {}) or {}),
        category_distribution=dict(getattr(final, "category_distribution", {}) or {}),
        warnings=list(getattr(final, "warnings", []) or []),
        user_warnings=user_warnings(final),
        points=[_point_to_schema(index, point) for index, point in enumerate(final.points, 1)],
        candidate_options=[_point_to_schema(index, point) for index, point in enumerate(getattr(final, "candidate_options", []) or [], 1)],
        explanation=explanation,
        debug_trace=list(getattr(final, "pipeline_trace", []) or []),
    )


def _point_to_schema(position: int, point: RoutePoint) -> UserRoutePoint:
    walk_mins = _optional_int(getattr(point, "estimated_walk_minutes", None))
    nav = navigation_payload(
        lat=float(point.lat),
        lng=float(point.lng),
        address=getattr(point, "address", None),
        estimated_walk_minutes=walk_mins,
    )
    return UserRoutePoint(
        place_id=str(getattr(point, "place_id", "")),
        city_slug=getattr(point, "city_slug", None),
        position=position,
        title=getattr(point, "title", None),
        address=getattr(point, "address", None),
        image_url=getattr(point, "image_url", None),
        short_description=getattr(point, "short_description", None),
        source=getattr(point, "source", None),
        lat=float(point.lat),
        lng=float(point.lng),
        category=str(getattr(point, "category", "") or ""),
        visit_minutes=int(getattr(point, "visit_minutes", 0) or 0),
        estimated_walk_minutes=walk_mins,
        estimated_arrival_time=_iso_dt(getattr(point, "estimated_arrival_time", None)),
        estimated_departure_time=_iso_dt(getattr(point, "estimated_departure_time", None)),
        time_status=getattr(point, "time_status", None),
        time_warning=getattr(point, "time_warning", None),
        scoring_breakdown=dict(getattr(point, "scoring_breakdown", {}) or {}),
        **nav,
    )


def _quality_status_from_breakdown(final: FinalRoute) -> str:
    breakdown = getattr(final, "quality_breakdown", {}) or {}
    status = breakdown.get("status") if isinstance(breakdown, dict) else None
    return str(status or "weak")


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _iso_dt(value: object) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
