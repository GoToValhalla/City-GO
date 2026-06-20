from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_budget_fit_service import (
    ROUTE_BUDGET_SINGLE_POINT_WARNING,
    ROUTE_BUDGET_TOO_TIGHT_WARNING,
    ROUTE_BUDGET_TRIMMED_WARNING,
    RouteBudgetFitService,
)


def _ctx(minutes: int) -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id=None,
        time_budget_minutes=minutes,
        effective_time_budget_minutes=minutes,
        interests=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=1500,
        effective_num_stops=4,
        min_stop_duration_minutes=20,
    )


def _point(place_id: str, visit: int, walk: int) -> SimpleNamespace:
    return SimpleNamespace(
        place_id=place_id,
        visit_minutes=visit,
        estimated_walk_minutes=walk,
    )


def test_fit_keeps_route_when_budget_allows() -> None:
    route = [_point("1", 20, 5), _point("2", 20, 5)]
    result = RouteBudgetFitService().fit(route, _ctx(60))
    assert result.route == route
    assert result.warnings == []


def test_fit_trims_tail_when_route_exceeds_budget() -> None:
    route = [_point("1", 20, 5), _point("2", 30, 5), _point("3", 20, 5)]
    result = RouteBudgetFitService().fit(route, _ctx(60))
    assert [point.place_id for point in result.route] == ["1", "2"]
    assert result.warnings == [ROUTE_BUDGET_TRIMMED_WARNING]


def test_fit_skips_oversized_middle_point_when_later_point_fits() -> None:
    route = [_point("1", 20, 5), _point("2", 60, 5), _point("3", 15, 5)]
    result = RouteBudgetFitService().fit(route, _ctx(50))
    assert [point.place_id for point in result.route] == ["1", "3"]
    assert result.warnings == [ROUTE_BUDGET_TRIMMED_WARNING, ROUTE_BUDGET_SINGLE_POINT_WARNING]


def test_fit_keeps_first_point_when_visit_fits_but_transfer_exceeds_budget() -> None:
    route = [_point("1", 20, 20), _point("2", 10, 5)]
    result = RouteBudgetFitService().fit(route, _ctx(30))
    assert [point.place_id for point in result.route] == ["1"]
    assert result.warnings == [ROUTE_BUDGET_SINGLE_POINT_WARNING]


def test_budget_fit_returns_empty_when_even_first_visit_exceeds_budget() -> None:
    route = [_point("oversized", 240, 80)]
    result = RouteBudgetFitService().fit(route, _ctx(30))
    assert result.route == []
    assert result.warnings == [ROUTE_BUDGET_TOO_TIGHT_WARNING]
    assert route == []
