from __future__ import annotations

from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_service import RoutePoint
from services.route_budget_fit_service import RouteBudgetFitService
from services.route_filter_reasons import budget_reason


def _ctx(*, minutes: int = 240, budget_level: BudgetLevel = BudgetLevel.FREE) -> MergedContext:
    return MergedContext(
        location=(43.238, 76.945),
        city_id="almaty",
        timezone="Asia/Almaty",
        time_budget_minutes=minutes,
        effective_time_budget_minutes=minutes,
        time_of_day=None,
        route_time_mode="flexible",
        interests=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=budget_level,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=6500,
        effective_num_stops=6,
        min_stop_duration_minutes=20,
    )


def _point(place_id: str, walk: int, visit: int) -> RoutePoint:
    point = RoutePoint(
        place_id=place_id,
        lat=43.238,
        lng=76.945,
        score=0.9,
        category="park",
        visit_minutes=visit,
    )
    point.estimated_walk_minutes = walk
    return point


def test_null_price_is_not_budget_blocker_new() -> None:
    place = SimpleNamespace(id="free-osm-park", price_level=None)

    assert budget_reason(place, _ctx(budget_level=BudgetLevel.FREE)) is None


def test_free_public_categories_without_price_pass_budget_reason_new() -> None:
    place = SimpleNamespace(id="park-without-price", category="park", price_level=None)

    assert budget_reason(place, _ctx(budget_level=BudgetLevel.FREE)) is None


def test_budget_fit_never_annihilates_non_empty_route_new() -> None:
    ctx = _ctx(minutes=60)
    route = [
        _point("too-long-first", walk=90, visit=60),
        _point("also-too-long", walk=30, visit=60),
    ]

    result = RouteBudgetFitService().fit(route, ctx)

    assert len(result.route) == 1
    assert result.route[0].place_id == "too-long-first"
    assert result.warnings


def test_budget_fit_keeps_full_route_within_overflow_tolerance_new() -> None:
    ctx = _ctx(minutes=100)
    route = [_point("park", walk=10, visit=45), _point("street", walk=10, visit=50)]

    result = RouteBudgetFitService().fit(route, ctx)

    assert [point.place_id for point in result.route] == ["park", "street"]
