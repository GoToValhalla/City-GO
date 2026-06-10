from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_finalize_service import RouteFinalizeService


def _ctx() -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id=None,
        time_budget_minutes=60,
        effective_time_budget_minutes=60,
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
        effective_num_stops=2,
        min_stop_duration_minutes=20,
    )


def _point() -> SimpleNamespace:
    return SimpleNamespace(
        place_id="1",
        lat=55.0,
        lng=20.0,
        visit_minutes=20,
        estimated_walk_minutes=5,
        time_status="ok",
    )


def test_finalize_includes_extra_route_warnings_once() -> None:
    warning = "Маршрут сокращён, чтобы уложиться в выбранный бюджет времени."
    final = RouteFinalizeService().finalize(
        [_point()],
        _ctx(),
        extra_warnings=[warning, warning],
    )
    assert final.warnings == [
        warning,
        "route_short_due_to_low_place_density",
        "some_places_have_no_address",
        "some_places_have_no_photo",
        "some_places_have_weak_description",
    ]
    assert final.has_warnings is True
    assert final.warning_count == 5


def test_finalize_empty_route_keeps_extra_warnings() -> None:
    warning = "Не нашли мест рядом с выбранным стартом."
    final = RouteFinalizeService().finalize([], _ctx(), extra_warnings=[warning])
    assert final.points == []
    assert final.warnings == [warning, "route_failed_no_places"]
    assert final.has_warnings is True
    assert final.warning_count == 2
