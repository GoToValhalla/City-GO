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
