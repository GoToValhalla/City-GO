from datetime import datetime

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_service import RoutePoint
from services.route_time_ordering_service import RouteTimeOrderingService


def _ctx() -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id=None,
        time_budget_minutes=120,
        effective_time_budget_minutes=96,
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


def _hours(close: str) -> dict[str, dict[str, str]]:
    return {"mon": {"open": "09:00", "close": close}}


def test_order_moves_nearby_closing_soon_place_earlier() -> None:
    route = (
        RoutePoint("late", 55.001, 20.0, 0.9, "park", 20, _hours("21:00")),
        RoutePoint("soon", 55.002, 20.0, 0.8, "museum", 20, _hours("10:45")),
    )

    ordered = RouteTimeOrderingService().order(route, _ctx(), datetime(2030, 6, 3, 10, 0))

    assert [point.place_id for point in ordered] == ["soon", "late"]


def test_order_keeps_far_closing_soon_place_in_original_position() -> None:
    route = (
        RoutePoint("late", 55.001, 20.0, 0.9, "park", 20, _hours("21:00")),
        RoutePoint("far", 56.0, 20.0, 0.8, "museum", 20, _hours("10:45")),
    )

    ordered = RouteTimeOrderingService().order(route, _ctx(), datetime(2030, 6, 3, 10, 0))

    assert [point.place_id for point in ordered] == ["late", "far"]
