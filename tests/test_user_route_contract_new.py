import pytest
from fastapi import HTTPException

from routers.user_routes import _ensure_current_route_matches
from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteState


def test_user_route_mutation_accepts_matching_route_id_new() -> None:
    _ensure_current_route_matches("route-1", _route_state("route-1"))


def test_user_route_mutation_rejects_mismatched_route_id_new() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _ensure_current_route_matches("route-new", _route_state("route-old"))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "route_state_conflict"
    assert exc_info.value.detail["route_id"] == "route-new"
    assert exc_info.value.detail["payload_route_id"] == "route-old"
    assert exc_info.value.detail["payload_revision"] == 4


def _route_state(route_id: str) -> UserRouteState:
    intent = UserRouteBuildRequest(
        lat=61.0042,
        lng=69.0019,
        city_id="khanty-mansiysk",
        time_budget_minutes=240,
    )
    return UserRouteState(
        route_id=route_id,
        revision=4,
        status="ready",
        context=intent,
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(
                place_id="1",
                position=1,
                title="Anchor cafe",
                address="Test address",
                lat=61.0042,
                lng=69.0019,
                category="cafe",
                visit_minutes=20,
            )
        ],
    )
