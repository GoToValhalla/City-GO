from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_adaptive_plan import prepare_route_plan
from services.route_assembly_service import RouteAssemblyService
from services.route_budget_fit_service import RouteBudgetFitService
from services.route_quality_gates import evaluate_quality_gates
from services.scoring_service import ScoredPlace


def _ctx(**overrides) -> MergedContext:
    data = {
        "location": (55.0, 20.0),
        "city_id": "test-city",
        "time_budget_minutes": 60,
        "effective_time_budget_minutes": 60,
        "interests": [],
        "avoided_categories": [],
        "avoided_place_ids": [],
        "budget_level": BudgetLevel.MID,
        "pace_mode": PaceMode.NORMAL,
        "pace_multiplier": 1.0,
        "local_vs_tourist": 0.5,
        "novelty_mode": False,
        "is_visiting": False,
        "visit_city_id": None,
        "visit_days": 1,
        "radius_meters": 5000,
        "effective_num_stops": 4,
        "min_stop_duration_minutes": 20,
    }
    data.update(overrides)
    return MergedContext(**data)


def _place(pid: int, category: str = "museum", lat: float = 55.0) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        title=f"P{pid}",
        lat=lat,
        lng=20.0,
        category=category,
        price_level=1,
        opening_hours=None,
        average_visit_duration_minutes=20,
        status="active",
        is_active=True,
    )


def _scored(count: int, category: str = "museum") -> list[ScoredPlace]:
    return [ScoredPlace(_place(index + 1, category, 55.0 + index * 0.0001), 0.8, {}) for index in range(count)]


def _gate(route: list[object], plan, eligible: int, **kwargs):
    return evaluate_quality_gates(route, plan, {"places_route_eligible": eligible}, kwargs.get("excluded", []), kwargs.get("avoided", []), kwargs.get("budget_zero", False))


def test_only_one_eligible_place_is_single_point_data_deficit() -> None:
    plan = prepare_route_plan(_scored(1), _ctx())
    route = RouteAssemblyService().build(plan.scored, _ctx())
    gate = _gate(route, plan, 1)
    assert gate.route_quality_status == "single_point"
    assert "city_data_deficit_single_eligible_place" in gate.warnings


def test_many_eligible_places_but_zero_route_is_algorithm_error() -> None:
    plan = prepare_route_plan(_scored(20), _ctx())
    gate = _gate([], plan, 100)
    assert gate.route_quality_status == "algorithm_error"
    assert "algorithm_error_many_eligible_places_no_route" in gate.warnings


def test_budget_fit_keeps_minimal_point_instead_of_silent_zero() -> None:
    route = [SimpleNamespace(place_id="1", visit_minutes=70, estimated_walk_minutes=10)]
    result = RouteBudgetFitService().fit(route, _ctx(time_budget_minutes=30, effective_time_budget_minutes=30))
    assert [point.place_id for point in result.route] == ["1"]
    assert result.warnings


def test_explicit_exclusion_violation_is_hard_failure() -> None:
    plan = prepare_route_plan(_scored(2), _ctx())
    route = RouteAssemblyService().build(plan.scored, _ctx())
    gate = _gate(route, plan, 20, excluded=[route[0].place_id])
    assert gate.route_quality_status == "failed"
    assert "route_violates_explicit_exclusions" in gate.warnings


def test_empty_opening_hours_do_not_block_flexible_route() -> None:
    route = RouteAssemblyService().build(prepare_route_plan(_scored(3), _ctx()).scored, _ctx())
    assert len(route) >= 1


def test_far_start_returns_honest_long_first_leg() -> None:
    scored = [ScoredPlace(_place(1, lat=56.0), 0.9, {})]
    route = RouteAssemblyService().build(prepare_route_plan(scored, _ctx()).scored, _ctx())
    assert len(route) == 1
    assert route[0].estimated_walk_minutes > 45
