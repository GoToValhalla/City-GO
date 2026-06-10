from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute
from schemas.user_route import UserRouteIntent
from services.user_route_mapper import final_route_to_state


def test_final_route_to_state_maps_points_and_context() -> None:
    point = RoutePoint("7", 54.96, 20.48, 0.8, "cafe", 25,
                       title="Кофейня", address="ул. Курортная", image_url="https://img")
    final = FinalRoute("route", [point], 25, 1, 0.2)
    intent = UserRouteIntent(lat=54.96, lng=20.48)
    state = final_route_to_state(final, intent)
    assert state.route_id == "route"
    assert state.context.lat == 54.96
    assert state.points[0].place_id == "7"
    assert state.points[0].title == "Кофейня"
    assert state.points[0].address == "ул. Курортная"
    assert state.points[0].image_url == "https://img"
