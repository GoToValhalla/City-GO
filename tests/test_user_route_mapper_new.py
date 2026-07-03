from types import SimpleNamespace

from schemas.user_route import UserRouteBuildRequest
from services.route_finalize_types import FinalRoute
from services.user_route_mapper import final_route_to_state


def test_user_route_mapper_accepts_fallback_metadata_new() -> None:
    point = SimpleNamespace(
        place_id="1",
        city_slug="khanty-mansiysk",
        title="",
        address=None,
        image_url="",
        short_description=None,
        source=None,
        lat=61.0042,
        lng=69.0019,
        category="museum",
        visit_minutes=30,
        estimated_walk_minutes=20,
        scoring_breakdown={"route_assembly_fallback": "emergency_seed", "long_walk_segment": True},
    )
    final = FinalRoute(
        route_id="route-1",
        status="partial_route",
        points=[point],
        total_minutes=30,
        total_places=1,
        estimated_distance=1.5,
    )
    intent = UserRouteBuildRequest(
        lat=61.0042,
        lng=69.0019,
        city_id="khanty-mansiysk",
        time_budget_minutes=240,
    )

    state = final_route_to_state(final, intent)

    assert state.total_places == 1
    assert state.points[0].title == "Место без названия"
    assert state.points[0].address == "Адрес уточняется"
    assert state.points[0].image_url is None
    assert state.points[0].scoring_breakdown["route_assembly_fallback"] == "emergency_seed"
    assert state.points[0].scoring_breakdown["long_walk_segment"] is True


def test_user_route_mapper_exposes_user_facing_warning_copy_new() -> None:
    final = FinalRoute(
        route_id="route-2",
        status="partial_route",
        points=[],
        total_minutes=0,
        total_places=0,
        estimated_distance=0.0,
        warnings=["route_builder_v2_insufficient_points", "unknown_internal_code"],
        has_warnings=True,
        warning_count=2,
    )
    intent = UserRouteBuildRequest(
        lat=40.1792,
        lng=44.4991,
        city_id="yerevan",
        time_budget_minutes=120,
    )

    state = final_route_to_state(final, intent)

    assert "route_builder_v2_insufficient_points" not in state.warnings
    assert "unknown_internal_code" not in state.warnings
    assert "После проверки осталось мало подходящих точек." in state.warnings
    assert "Маршрут собран с ограничениями по данным." in state.warnings
    assert {warning.type for warning in state.user_warnings} <= {"route", "data", "budget", "walk", "interest"}
    assert all("_" not in warning.type for warning in state.user_warnings)
