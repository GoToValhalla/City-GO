from __future__ import annotations

from datetime import datetime
from typing import Any

from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute
from services.route_address_warnings import missing_address_warning_items, route_warnings_with_missing_address
from services.route_navigation_service import navigation_payload
from services.route_pipeline_trace import compact_route_trace, route_debug_summary
from services.route_user_warnings import user_warnings

UNKNOWN_ADDRESS = "Адрес уточняется"
UNKNOWN_TITLE = "Место без названия"


def serialize_final_route(final: FinalRoute) -> dict[str, object]:
    pipeline_trace = list(getattr(final, "pipeline_trace", []) or [])
    points = list(getattr(final, "points", []) or [])
    candidate_options = list(getattr(final, "candidate_options", []) or [])
    return {
        "route_id": str(final.route_id),
        "status": str(getattr(final, "status", "ready") or "ready"),
        "partial_reason": getattr(final, "partial_reason", None),
        "total_places": int(getattr(final, "total_places", len(points)) or len(points)),
        "total_minutes": int(getattr(final, "total_minutes", 0) or 0),
        "total_estimated_minutes": int(getattr(final, "total_estimated_minutes", 0) or 0),
        "estimated_distance": float(getattr(final, "estimated_distance", 0.0) or 0.0),
        "estimated_end_time": _iso_dt(getattr(final, "estimated_end_time", None)),
        "has_warnings": bool(getattr(final, "has_warnings", False)),
        "warning_count": int(getattr(final, "warning_count", 0) or 0),
        "places_with_warnings": list(getattr(final, "places_with_warnings", []) or []),
        "quality_score": float(getattr(final, "quality_score", 0.0) or 0.0),
        "quality_status": str(getattr(final, "quality_status", "weak") or "weak"),
        "quality_breakdown": _safe_dict(getattr(final, "quality_breakdown", {}) or {}),
        "route_quality_status": str(getattr(final, "route_quality_status", "") or ""),
        "route_completeness": float(getattr(final, "route_completeness", 0.0) or 0.0),
        "matched_interest_count": int(getattr(final, "matched_interest_count", 0) or 0),
        "total_requested_interests": int(getattr(final, "total_requested_interests", 0) or 0),
        "expansion_level": str(getattr(final, "expansion_level", "none") or "none"),
        "expanded_category_count": int(getattr(final, "expanded_category_count", 0) or 0),
        "neutral_added_count": int(getattr(final, "neutral_added_count", 0) or 0),
        "fallback_level": str(getattr(final, "fallback_level", "none") or "none"),
        "user_explanation": getattr(final, "user_explanation", None),
        "total_walk_distance_meters": int(getattr(final, "total_walk_distance_meters", 0) or 0),
        "time_breakdown": dict(getattr(final, "time_breakdown", {}) or {}),
        "category_distribution": dict(getattr(final, "category_distribution", {}) or {}),
        "warnings": route_warnings_with_missing_address(
            list(getattr(final, "warnings", []) or []),
            points,
        ),
        "user_warnings": [*user_warnings(final), *missing_address_warning_items(points)],
        "points": [_serialize_point(point) for point in points],
        "candidate_options": [_serialize_point(point) for point in candidate_options],
        "route_debug_summary": route_debug_summary(str(final.route_id), pipeline_trace),
        "debug_trace": compact_route_trace(pipeline_trace),
    }


def _serialize_point(point: RoutePoint) -> dict[str, object]:
    lat = _float_or_zero(getattr(point, "lat", 0.0))
    lng = _float_or_zero(getattr(point, "lng", 0.0))
    address = _text_or_default(getattr(point, "address", None), UNKNOWN_ADDRESS)
    walk_mins = _optional_int(getattr(point, "estimated_walk_minutes", None))
    nav = navigation_payload(
        lat=lat,
        lng=lng,
        address=address,
        estimated_walk_minutes=walk_mins,
        category=str(getattr(point, "category", "") or "") or None,
    )
    return {
        "place_id": str(getattr(point, "place_id", "")),
        "city_slug": getattr(point, "city_slug", None),
        "title": _text_or_default(getattr(point, "title", None), UNKNOWN_TITLE),
        "address": address,
        "image_url": _text_or_none(getattr(point, "image_url", None)),
        "short_description": _text_or_none(getattr(point, "short_description", None)),
        "source": _text_or_none(getattr(point, "source", None)),
        "lat": lat,
        "lng": lng,
        "category": str(getattr(point, "category", "") or ""),
        "visit_minutes": int(getattr(point, "visit_minutes", 0) or 0),
        "estimated_walk_minutes": walk_mins,
        "estimated_arrival_time": _iso_dt(getattr(point, "estimated_arrival_time", None)),
        "estimated_departure_time": _iso_dt(getattr(point, "estimated_departure_time", None)),
        "time_status": getattr(point, "time_status", None),
        "time_warning": getattr(point, "time_warning", None),
        "scoring_breakdown": _safe_dict(getattr(point, "scoring_breakdown", {}) or {}),
        **nav,
    }


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