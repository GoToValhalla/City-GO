from __future__ import annotations

import pytest

from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteSessionActionRequest, UserRouteSessionStartRequest, UserRouteState
from services.user_route_session_service import UserRouteSessionError, UserRouteSessionService


def _route_state(city_slug: str, place_ids: list[int]) -> UserRouteState:
    intent = UserRouteBuildRequest(lat=43.238949, lng=76.889709, city_id=city_slug, time_budget_minutes=120)
    points = [
        UserRoutePoint(
            place_id=str(place_id),
            city_slug=city_slug,
            position=index,
            title=f"Point {index}",
            address="Main street",
            lat=43.238949 + index / 1000,
            lng=76.889709 + index / 1000,
            category="museum",
            visit_minutes=20,
        )
        for index, place_id in enumerate(place_ids, 1)
    ]
    return UserRouteState(
        route_id="session-route",
        status="ready",
        context=intent,
        total_places=len(points),
        total_minutes=80,
        total_estimated_minutes=100,
        estimated_distance=2.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.9,
        quality_status="good",
        warnings=[],
        points=points,
        explanation={"summary": "Session route"},
        debug_trace=[],
    )


def _start_session(db_session, city_factory, place_factory):
    city = city_factory(slug="session-city", name="Session City")
    first = place_factory(city_id=city.id, slug="session-place-1", title="Session Place 1", category="museum")
    second = place_factory(city_id=city.id, slug="session-place-2", title="Session Place 2", category="park")
    route = _route_state(city.slug, [first.id, second.id])
    return UserRouteSessionService().start(db_session, UserRouteSessionStartRequest(current_route=route, user_id="user-1"))


def test_user_route_session_start_rejects_empty_route_new(db_session) -> None:
    empty = _route_state("missing-city", [])

    with pytest.raises(UserRouteSessionError, match="Cannot start an empty route"):
        UserRouteSessionService().start(db_session, UserRouteSessionStartRequest(current_route=empty, user_id="user-1"))


def test_user_route_session_start_creates_active_session_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)

    assert state.status == "active"
    assert state.current_point_index == 0
    assert state.current_place_id is not None
    assert len(state.points) == 2
    assert state.points[0].is_current is True


def test_user_route_session_start_is_idempotent_for_active_session_new(db_session, city_factory, place_factory) -> None:
    first = _start_session(db_session, city_factory, place_factory)
    city_route = _route_state("session-city", [int(point.place_id) for point in first.points])

    second = UserRouteSessionService().start(db_session, UserRouteSessionStartRequest(current_route=city_route, user_id="user-1"))

    assert second.session_id == first.session_id
    assert second.status == "active"


def test_user_route_session_pause_and_resume_transition_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)

    paused = UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="pause"))
    resumed = UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="resume"))

    assert paused.status == "paused"
    assert paused.paused_at is not None
    assert resumed.status == "active"
    assert resumed.paused_at is None


def test_user_route_session_rejects_invalid_resume_from_active_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)

    with pytest.raises(UserRouteSessionError, match="Invalid session transition from active"):
        UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="resume"))


def test_user_route_session_complete_point_advances_to_next_point_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)
    first_place_id = state.current_place_id

    updated = UserRouteSessionService().apply_action(
        db_session,
        state.session_id,
        UserRouteSessionActionRequest(action="complete_point", place_id=first_place_id),
    )

    assert updated.status == "active"
    assert updated.current_point_index == 1
    assert first_place_id in updated.point_completed_at
    assert updated.points[0].is_visited is True
    assert updated.points[1].is_current is True


def test_user_route_session_skip_last_open_point_completes_route_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)
    after_first = UserRouteSessionService().apply_action(
        db_session,
        state.session_id,
        UserRouteSessionActionRequest(action="complete_point", place_id=state.current_place_id),
    )

    completed = UserRouteSessionService().apply_action(
        db_session,
        state.session_id,
        UserRouteSessionActionRequest(action="skip_point", place_id=after_first.current_place_id),
    )

    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert after_first.current_place_id in completed.skipped_place_ids


def test_user_route_session_rejects_action_after_completed_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)
    completed = UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="finish"))

    with pytest.raises(UserRouteSessionError, match="already finished"):
        UserRouteSessionService().apply_action(db_session, completed.session_id, UserRouteSessionActionRequest(action="pause"))


def test_user_route_session_abandon_is_terminal_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)

    abandoned = UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="abandon"))

    assert abandoned.status == "abandoned"
    assert abandoned.completed_at is not None


def test_user_route_session_rejects_missing_target_point_new(db_session, city_factory, place_factory) -> None:
    state = _start_session(db_session, city_factory, place_factory)

    with pytest.raises(UserRouteSessionError, match="Route session point not found"):
        UserRouteSessionService().apply_action(db_session, state.session_id, UserRouteSessionActionRequest(action="complete_point", place_id="999999"))
