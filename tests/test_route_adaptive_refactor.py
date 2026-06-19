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
        "time_budget_minutes": 120,
        "effective_time_budget_minutes": 120,
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
        "effective_num_stops": 6,
        "min_stop_duration_minutes": 20,
    }
    data.update(overrides)
    return MergedContext(**data)


def _place(pid: int, category: str, lat: float | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        title=f"P{pid}",
        lat=55.0 + pid * 0.0001 if lat is None else lat,
        lng=20.0,
        category=category,
        price_level=1,
        opening_hours=None,
        average_visit_duration_minutes=20,
        status="active",
        is_active=True,
    )


def _scored(categories: list[str]) -> list[ScoredPlace]:
    return [ScoredPlace(_place(index + 1, category), 0.8, {}) for index, category in enumerate(categories)]


def test_no_interests_uses_neutral_pool_without_hidden_walk() -> None:
    plan = prepare_route_plan(_scored(["museum", "park", "cafe"] * 334), _ctx(interests=[]))
    assert plan.expansion_level == "neutral"
    assert plan.target_points >= 1
    assert "route_built_without_selected_interests" in plan.warnings


def test_zero_exact_interest_expands_with_warning() -> None:
    plan = prepare_route_plan(_scored(["cafe", "park", "gallery"]), _ctx(interests=["bar"]))
    assert plan.exact_count == 0
    assert plan.expansion_level in {"mixed", "short"}
    assert "selected_interests_have_no_exact_matches" in plan.warnings


def test_single_exact_match_becomes_anchor_in_route() -> None:
    scored = _scored(["museum", "cafe", "park"])
    plan = prepare_route_plan(scored, _ctx(interests=["architecture"]))
    route = RouteAssemblyService().build(plan.scored, _ctx(interests=["architecture"]))
    assert plan.exact_count == 1
    assert route[0].place_id == "1"
    assert route[0].scoring_breakdown["route_anchor"] == 1.0


def test_many_exact_matches_stay_primary() -> None:
    plan = prepare_route_plan(_scored(["museum"] * 6 + ["cafe"] * 3), _ctx(interests=["architecture"]))
    assert plan.exact_count == 6
    assert plan.expansion_level == "primary"
    assert plan.neutral_added_count == 0


def test_sparse_city_target_does_not_exceed_available_pool() -> None:
    plan = prepare_route_plan(_scored(["museum", "park"]), _ctx(time_budget_minutes=240, effective_time_budget_minutes=240))
    assert plan.target_points == 2


def test_short_and_long_budgets_are_adaptive_not_fixed_five() -> None:
    short = prepare_route_plan(_scored(["museum"] * 20), _ctx(time_budget_minutes=60, effective_time_budget_minutes=60))
    long = prepare_route_plan(_scored(["museum"] * 20), _ctx(time_budget_minutes=240, effective_time_budget_minutes=240))
    assert 1 <= short.target_points <= 2
    assert long.target_points != 5


def test_same_category_pool_still_builds_honest_route() -> None:
    route = RouteAssemblyService().build(prepare_route_plan(_scored(["coffee"] * 8), _ctx()).scored, _ctx())
    assert len(route) >= 1
    assert all(point.category == "coffee" for point in route)
