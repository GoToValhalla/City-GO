from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, Header, Request, Response
from services.city_service import get_city_by_id
from services.feature_toggle_guards import assert_ai_recommendations
from services.route_toggle_guard import assert_route_generation_allowed
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.recommendation_route import (
    RecommendationRouteRequest,
    RecommendationRouteResponse,
)
from services.context_merge_service import RequestContext
from services.explainability_service import ExplainabilityService
from services.route_builder_service import RouteBuilderService
from services.route_analytics_service import record_route_build
from services.recommendation_route_serializer import serialize_final_route
from services.product_event_service import record_event
from services.user_profile_from_signals_service import build_user_profile_from_signals

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
CANONICAL_ROUTE_ENDPOINT = "/v1/recommendations/route"
LEGACY_ROUTE_ENDPOINT = "/recommendations/route"
SUNSET_HTTP_DATE = "Tue, 30 Jun 2026 00:00:00 GMT"


def _set_legacy_deprecation_headers(request: Request, response: Response) -> None:
    if request.url.path != LEGACY_ROUTE_ENDPOINT:
        return
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = SUNSET_HTTP_DATE
    response.headers["Link"] = f'<{CANONICAL_ROUTE_ENDPOINT}>; rel="successor-version"'


@router.post("/route", response_model=RecommendationRouteResponse)
def post_recommendation_route(
    payload: RecommendationRouteRequest,
    request: Request,
    response: Response,
    x_debug: str | None = Header(default=None, alias="X-Debug"),
    db: Session = Depends(get_db),
) -> RecommendationRouteResponse:
    started = perf_counter()
    city_slug = _resolve_city_slug(db, payload.city_slug, payload.city_id)
    assert_route_generation_allowed(db, city_slug=city_slug)
    assert_ai_recommendations(db, city_slug=city_slug)
    _set_legacy_deprecation_headers(request, response)
    route_request = RequestContext(
        location=(payload.lat, payload.lng),
        city_id=payload.city_id,
        time_budget_minutes=payload.time_budget_minutes,
        time_of_day=payload.time_of_day,
        route_time_mode=payload.route_time_mode,
        interests=payload.interests,
        avoided_categories=payload.avoided_categories,
        excluded_place_ids=payload.excluded_place_ids,
        budget_level=payload.budget_level,
        pace_mode=payload.pace_mode,
        is_visiting=payload.is_visiting,
        visit_city_id=payload.visit_city_id,
        visit_days=payload.visit_days,
    )

    builder = RouteBuilderService()
    profile = build_user_profile_from_signals(db, payload.user_id)
    final_route = builder.build_route(db=db, request=route_request, profile=profile)
    record_route_build(
        db,
        final_route,
        source="recommendations",
        latency_ms=_latency_ms(started),
        city_id=payload.city_id,
        user_id=payload.user_id,
    )
    stops = len(getattr(final_route, "stops", []) or [])
    evt = "route_generation_success" if stops > 0 else "route_generation_failed"
    record_event(db, event_type=evt, city_slug=city_slug, user_id=payload.user_id,
                 payload={"stops": stops, "source": "recommendations"})

    explainer = ExplainabilityService()
    explanation = explainer.build_route_explanation(final_route)

    body = serialize_final_route(final_route)
    body["explanation"] = explanation
    if _debug_enabled(x_debug):
        body["_trace"] = list(getattr(final_route, "pipeline_trace", []) or [])

    return RecommendationRouteResponse.model_validate(body)


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _debug_enabled(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "debug"}


def _resolve_city_slug(db: Session, city_slug: str | None, city_id: str | None) -> str | None:
    if city_slug:
        return city_slug
    if not city_id or not city_id.isdigit():
        return None
    city = get_city_by_id(db, int(city_id))
    return city.slug if city else None
