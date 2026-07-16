"""Regression for the production route_quick blocker: POST /api/v1/user-routes/build
returned HTTP 200 with status=failed, quality_status=failed, total_places=0,
debug_trace final stage=final_response, for a zero-candidate Yerevan request.

Root cause: services/route_builder_flow.py::_apply_adaptive_metadata()
overwrote the already-correct final_route.status (set by
RouteFinalizeService/route_status_service.route_status() to "no_route" for
zero points) with "failed" whenever route_quality_status == "failed" —
without checking whether the route actually had points. route_quality_status
== "failed" is returned by services/route_quality_gates.py::_status() for
TWO different situations: a route that violates an explicit user exclusion
(a real algorithm bug — points exist and shouldn't) and an empty route
(`if not route: return "failed"` — an honest "found nothing", not a bug).
Only the first case is a genuine failure.

Fix: final_route.status is only forced to "failed" when route_quality_status
== "algorithm_error", or route_quality_status == "failed" AND the route
genuinely has points (the exclusion-violation case). An empty route keeps
the honest "no_route" status that RouteFinalizeService already computed.

scripts/production_smoke.py's route_quick check now also treats "no_route"
as a failing status (it previously only checked
failed/empty/preview_failed) — this is additive, not a weakening: a
genuinely empty route already failed smoke before this fix (as "failed");
after this fix it fails smoke under its own honest status name instead.
"""

from __future__ import annotations

from services.candidate_retrieval_service import CandidateRetrievalService
from services.context_merge_service import ContextMergeService, RequestContext
from services.route_builder_service import RouteBuilderService
from scripts.production_smoke import validate_route_response
import json


YEREVAN_LAT = 40.1792
YEREVAN_LNG = 44.4991


def _yerevan_request(**overrides) -> RequestContext:
    base = dict(
        location=(YEREVAN_LAT, YEREVAN_LNG),
        city_id="yerevan",
        time_budget_minutes=120,
        interests=["architecture", "history"],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
    )
    base.update(overrides)
    return RequestContext(**base)


# --- exact Yerevan production request regression ---


def test_exact_yerevan_request_reports_honest_no_route_not_failed_new(db_session, city_factory):
    """Reproduces the exact production defect: a city with zero eligible
    places at the requested point must report status="no_route" (honest),
    not the misleading status="failed" that was actually returned in
    production for this exact request shape."""
    city_factory(
        slug="yerevan", name="Yerevan", center_lat=YEREVAN_LAT, center_lng=YEREVAN_LNG,
        launch_status="published", is_active=True,
    )

    builder = RouteBuilderService()
    final = builder.build_route(db=db_session, request=_yerevan_request(), profile=None)

    assert final.status == "no_route"
    assert final.route_quality_status == "failed"
    assert len(getattr(final, "points", []) or []) == 0
    assert final.pipeline_trace[-1]["stage"] == "final_response"


def test_exact_yerevan_request_via_http_endpoint_new(client, city_factory):
    """Same reproduction through the real HTTP endpoint with the exact
    production request body."""
    city_factory(
        slug="yerevan", name="Yerevan", center_lat=YEREVAN_LAT, center_lng=YEREVAN_LNG,
        launch_status="published", is_active=True,
    )
    payload = {
        "build_mode": "auto",
        "city_id": "yerevan",
        "lat": YEREVAN_LAT,
        "lng": YEREVAN_LNG,
        "start_source": "map_point",
        "start": {"type": "map_point", "lat": YEREVAN_LAT, "lng": YEREVAN_LNG},
        "mode": "quick",
        "time_budget_minutes": 120,
        "interests": ["architecture", "history"],
    }

    response = client.post("/v1/user-routes/build", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_route"
    assert body["total_places"] == 0


# --- positive route with eligible candidates ---


def test_yerevan_with_eligible_candidate_returns_a_route_new(db_session, city_factory, place_factory):
    city = city_factory(
        slug="yerevan", name="Yerevan", center_lat=YEREVAN_LAT, center_lng=YEREVAN_LNG,
        launch_status="published", is_active=True,
    )
    place_factory(
        slug="cascade-complex", title="Cascade Complex", city_id=city.id,
        category="architecture", lat=40.1805, lng=44.5115,
    )

    builder = RouteBuilderService()
    final = builder.build_route(db=db_session, request=_yerevan_request(), profile=None)

    assert final.status in {"ready", "partial_route", "single_point"} or len(final.points) >= 1
    assert len(final.points) >= 1


# --- zero-candidate honest failure across the stack ---


def test_zero_candidates_produces_zero_length_trace_chain_new(db_session, city_factory):
    city_factory(slug="empty-city", name="Empty City", center_lat=10.0, center_lng=10.0, launch_status="published", is_active=True)
    request = _yerevan_request(location=(10.0, 10.0), city_id="empty-city")

    svc = CandidateRetrievalService()
    merge = ContextMergeService()
    ctx = merge.merge(request, profile=None)
    candidates = svc.get_candidates(db_session, ctx)
    assert candidates == []

    builder = RouteBuilderService()
    final = builder.build_route(db=db_session, request=request, profile=None)
    assert final.status == "no_route"
    assert final.total_places == 0


def test_zero_candidates_does_not_fabricate_places_new(db_session, city_factory):
    city_factory(slug="fabrication-check", center_lat=1.0, center_lng=1.0, launch_status="published", is_active=True)
    request = _yerevan_request(location=(1.0, 1.0), city_id="fabrication-check")

    builder = RouteBuilderService()
    final = builder.build_route(db=db_session, request=request, profile=None)

    assert final.points == []
    assert final.total_places == 0


# --- status mapping consistency: algorithm_error and exclusion-violation stay "failed" ---


def test_algorithm_error_quality_status_still_forces_failed_status_new():
    from services.route_builder_flow import _apply_adaptive_metadata
    from services.route_quality_gates import QualityGateResult
    from services.route_adaptive_types import RoutePlan
    from types import SimpleNamespace

    final_route = SimpleNamespace(status="no_route", total_places=0)
    gate = QualityGateResult(
        route_quality_status="algorithm_error", route_completeness=0.0, fallback_level="none",
        warnings=["algorithm_error_many_eligible_places_no_route"], partial_reason="algorithm_error_many_eligible_places_no_route",
    )
    plan = RoutePlan(scored=[], target_points=4, exact_count=0, related_count=0, neutral_count=0, expansion_level="primary", expanded_category_count=0, neutral_added_count=0, warnings=[], user_explanation="")
    ctx = SimpleNamespace(interests=[])

    _apply_adaptive_metadata(final_route, plan, gate, ctx)

    assert final_route.status == "failed"


def test_exclusion_violation_with_nonempty_route_still_forces_failed_status_new():
    """route_quality_status == "failed" with a NON-EMPTY route (the
    route_violates_explicit_exclusions case) is a real algorithm bug and
    must still force status="failed" — only the empty-route case was
    changed by this fix."""
    from services.route_builder_flow import _apply_adaptive_metadata
    from services.route_quality_gates import QualityGateResult
    from services.route_adaptive_types import RoutePlan
    from types import SimpleNamespace

    final_route = SimpleNamespace(status="ready", total_places=1)
    gate = QualityGateResult(
        route_quality_status="failed", route_completeness=0.0, fallback_level="none",
        warnings=["route_violates_explicit_exclusions"], partial_reason="route_violates_explicit_exclusions",
    )
    plan = RoutePlan(scored=[], target_points=4, exact_count=0, related_count=0, neutral_count=0, expansion_level="primary", expanded_category_count=0, neutral_added_count=0, warnings=[], user_explanation="")
    ctx = SimpleNamespace(interests=[])

    _apply_adaptive_metadata(final_route, plan, gate, ctx)

    assert final_route.status == "failed"


def test_empty_route_with_failed_quality_status_keeps_honest_no_route_status_new():
    from services.route_builder_flow import _apply_adaptive_metadata
    from services.route_quality_gates import QualityGateResult
    from services.route_adaptive_types import RoutePlan
    from types import SimpleNamespace

    final_route = SimpleNamespace(status="no_route", total_places=0)
    gate = QualityGateResult(
        route_quality_status="failed", route_completeness=0.0, fallback_level="none",
        warnings=[], partial_reason=None,
    )
    plan = RoutePlan(scored=[], target_points=4, exact_count=0, related_count=0, neutral_count=0, expansion_level="primary", expanded_category_count=0, neutral_added_count=0, warnings=[], user_explanation="")
    ctx = SimpleNamespace(interests=[])

    _apply_adaptive_metadata(final_route, plan, gate, ctx)

    assert final_route.status == "no_route"


# --- no hidden/ineligible/service places in route ---


def test_route_never_includes_hidden_or_ineligible_places_new(db_session, city_factory, place_factory):
    city = city_factory(
        slug="yerevan-hidden-check", name="Yerevan Hidden Check", center_lat=YEREVAN_LAT, center_lng=YEREVAN_LNG,
        launch_status="published", is_active=True,
    )
    place_factory(
        slug="visible-place", title="Cascade Complex", city_id=city.id,
        category="architecture", lat=40.1805, lng=44.5115,
    )
    place_factory(
        slug="hidden-place", title="Hidden Draft", city_id=city.id,
        category="architecture", lat=40.1806, lng=44.5116,
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False, publication_status="draft",
    )
    place_factory(
        slug="service-place", title="ATM", city_id=city.id,
        category="atm", lat=40.1807, lng=44.5117,
    )

    request = _yerevan_request(city_id="yerevan-hidden-check")
    builder = RouteBuilderService()
    final = builder.build_route(db=db_session, request=request, profile=None)

    slugs = {point.place_id for point in final.points}
    assert "hidden-place" not in slugs
    assert "service-place" not in slugs


# --- production_smoke route_quick treats no_route as failing (does not silently pass) ---


def test_smoke_route_quick_fails_on_no_route_status_new():
    result = validate_route_response(json.dumps({"status": "no_route", "total_places": 0}), 200)

    assert not result.ok
    assert result.detail.startswith("status_no_route")


def test_smoke_route_quick_still_fails_on_failed_status_new():
    """Existing failed/empty/preview_failed behavior is unchanged."""
    for status in ("failed", "empty", "preview_failed"):
        result = validate_route_response(json.dumps({"status": status, "total_places": 0}), 200)
        assert not result.ok
        assert result.detail.startswith(f"status_{status}")


def test_smoke_route_quick_still_passes_on_ready_status_new():
    result = validate_route_response(json.dumps({"status": "ready", "total_places": 3}), 200)

    assert result.ok
