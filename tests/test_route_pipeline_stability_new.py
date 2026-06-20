from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from services.context_merge_service import ContextMergeService, RequestContext
from services.hard_filters_service import HardFiltersService
from services.route_adaptive_plan import prepare_route_plan
from services.route_assembly_service import RouteAssemblyService
from services.route_builder_flow import _failure_stage, _route
from services.route_budget_fit_service import RouteBudgetFitService
from services.route_pipeline_trace import RoutePipelineTrace
from services.route_quality_gates import evaluate_quality_gates
from services.scoring_service import ScoredPlace, ScoringService


def _place(pid: int, category: str, score_lat: float = 61.0) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid, title=f"Place {pid}", lat=score_lat + pid * 0.0001, lng=69.0 + pid * 0.0001,
        category=category, price_level=1, status="active", is_active=True, opening_hours=None,
        average_visit_duration_minutes=25, effective_visit_duration_minutes=25, address="Test",
        short_description="Test", source="test", city=SimpleNamespace(slug="khanty-test"),
        validation={"is_valid": True, "issues": []},
    )


def _ctx() -> object:
    return ContextMergeService().merge(
        RequestContext(
            location=(61.0, 69.0), city_id="khanty-test", time_budget_minutes=240,
            interests=["coffee", "food", "walk", "quiet", "museum"],
            avoided_categories=["bars", "museums", "restaurants"],
        ),
        None,
    )


def test_khanty_route_with_interests_and_exclusions_returns_minimal_route() -> None:
    ctx = _ctx()
    places = [_place(1, "coffee"), _place(2, "park"), _place(3, "walk"), _place(4, "food"),
              _place(5, "museum"), _place(6, "restaurant"), _place(7, "bar")]
    with patch("services.hard_filters_service.is_place_open_at", return_value=None):
        filtered = HardFiltersService().apply(places, ctx, datetime(2030, 1, 1, 12, 0, 0))
    scored = ScoringService().score(filtered, ctx)
    route = RouteBudgetFitService().fit(RouteAssemblyService().build(prepare_route_plan(scored, ctx).scored, ctx), ctx).route
    assert len(route) >= 1
    assert "museum" not in ctx.interests
    assert not {point.category for point in route} & {"bar", "museum", "restaurant"}


def test_assembly_zero_is_recovered_by_minimal_fallback() -> None:
    ctx = _ctx()
    scored = [ScoredPlace(_place(1, "coffee"), 0.91, {}), ScoredPlace(_place(2, "park"), 0.82, {})]
    deps = SimpleNamespace(
        assembly=SimpleNamespace(build=lambda _scored, _ctx: []),
        time_ordering=SimpleNamespace(order=lambda route, _ctx, _now: route),
        time=SimpleNamespace(apply=lambda route, _ctx, _now: route),
    )
    trace = RoutePipelineTrace()
    route, warnings = _route(deps, scored, [], ctx, datetime(2030, 1, 1, 12, 0, 0), trace, 2)
    assembly = next(item for item in trace.snapshot() if item["stage"] == "assembly")
    assert len(route) == 2
    assert "assembly_zero_recovered_by_minimal_fallback" in warnings
    assert assembly["fallback_used"] is True


def test_many_eligible_places_no_route_sets_algorithm_error_with_failure_stage() -> None:
    ctx = _ctx()
    scored = [ScoredPlace(_place(1, "coffee"), 0.9, {})]
    plan = prepare_route_plan(scored, ctx)
    gate = evaluate_quality_gates([], plan, {"places_route_eligible": 215}, [], [], False)
    stage = _failure_stage([object()], [object()], scored, [], [], gate)
    assert gate.route_quality_status == "algorithm_error"
    assert "algorithm_error_many_eligible_places_no_route" in gate.warnings
    assert stage == "assembly"
