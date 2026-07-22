from __future__ import annotations

import threading

from db.session import SessionLocal
from models.route import Route
from models.route_session import RouteSession, RouteSessionPoint
from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteSessionActionRequest, UserRouteSessionStartRequest, UserRouteState
from services.user_route_session_service import UserRouteSessionError, UserRouteSessionService
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)
from tests_postgres_integration.conftest import make_published_place


def _route(place, city_slug: str, route_id: str) -> UserRouteState:
    return UserRouteState(
        route_id=route_id,
        revision=1,
        context=UserRouteIntent(lat=float(place.lat), lng=float(place.lng), city_id=city_slug, time_budget_minutes=120),
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[UserRoutePoint(place_id=str(place.id), city_slug=city_slug, position=1, title=place.title, lat=float(place.lat), lng=float(place.lng), category=str(place.category), visit_minutes=20)],
    )


def test_only_one_concurrent_mutation_can_advance_one_revision_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    issued = register_initial_route_state(pg_session, _route(place, pg_city.slug, f"route-race-{place.id}"))
    pg_session.commit()
    payload = issued.model_dump(mode="json")
    start = threading.Barrier(2)
    results: list[str] = []

    def mutate(label: str) -> None:
        session = SessionLocal()
        try:
            previous = UserRouteState.model_validate(payload)
            start.wait(timeout=5)
            registry = verify_current_route_state(session, previous, lock=True)
            next_state = previous.model_copy(update={"warnings": [label], "has_warnings": True, "warning_count": 1})
            advance_route_state(session, previous=previous, next_state=next_state, registry=registry)
            session.commit()
            results.append("success")
        except UserRouteStateConflictError:
            session.rollback()
            results.append("conflict")
        finally:
            session.close()

    threads = [threading.Thread(target=mutate, args=(label,)) for label in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results) == ["conflict", "success"]
    pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id == issued.route_id).delete()
    pg_session.commit()


def test_concurrent_terminal_actions_cannot_overwrite_same_session_point_new(pg_session, pg_city, pg_category) -> None:
    # This test needs a route with a SECOND open point so that finalizing
    # the first point does not also auto-complete the whole session
    # (_advance_current_index completes the session only once no open
    # point remains). A local, two-point route is built here instead of
    # reusing the shared _route() helper (which always builds exactly one
    # point and is also used by test_only_one_concurrent_mutation_..._new
    # above -- changing it would affect that test too).
    first_place = make_published_place(pg_session, city=pg_city, category=pg_category)
    second_place = make_published_place(pg_session, city=pg_city, category=pg_category)
    route = UserRouteState(
        route_id=f"session-race-{first_place.id}",
        revision=1,
        context=UserRouteIntent(lat=float(first_place.lat), lng=float(first_place.lng), city_id=pg_city.slug, time_budget_minutes=120),
        total_places=2,
        total_minutes=40,
        total_estimated_minutes=40,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(place_id=str(first_place.id), city_slug=pg_city.slug, position=1, title=first_place.title, lat=float(first_place.lat), lng=float(first_place.lng), category=str(first_place.category), visit_minutes=20),
            UserRoutePoint(place_id=str(second_place.id), city_slug=pg_city.slug, position=2, title=second_place.title, lat=float(second_place.lat), lng=float(second_place.lng), category=str(second_place.category), visit_minutes=20),
        ],
    )
    issued = register_initial_route_state(pg_session, route)
    state = UserRouteSessionService().start(pg_session, UserRouteSessionStartRequest(current_route=issued, user_id="pg-user"))
    pg_session.commit()
    # Captured as a plain value before threads start: `first_place` is a
    # SQLAlchemy ORM object bound to pg_session, and pg_session.commit()
    # above expires its attributes -- if two background threads both
    # touch `first_place.id` afterwards, SQLAlchemy tries to lazily reload
    # it via pg_session from two threads at once ("This session is
    # provisioning a new connection; concurrent operations are not
    # permitted"), since Session objects are not thread-safe. Reading it
    # once here, before the race starts, removes any live ORM object from
    # the thread closures. Both threads target this SAME (first) point,
    # so the winning commit finalizes only that point, leaving the
    # second point open -- the losing thread must then re-read the
    # committed row and observe that specific point already finalized.
    first_place_id = str(first_place.id)
    start = threading.Barrier(2)
    results: list[str] = []
    conflict_messages: list[str] = []

    def act(action: str) -> None:
        session = SessionLocal()
        try:
            start.wait(timeout=5)
            UserRouteSessionService().apply_action(session, state.session_id, UserRouteSessionActionRequest(action=action, place_id=first_place_id, route_id=state.route_id), ownership_token=state.ownership_token)
            session.commit()
            results.append("success")
        except UserRouteSessionError as exc:
            # Only the expected business rejection counts as a legitimate
            # concurrency conflict -- anything else (a bug, a connection
            # error, an unrelated crash) must fail the test loudly instead
            # of being silently absorbed as if it were the race being
            # verified here.
            session.rollback()
            results.append("conflict")
            conflict_messages.append(str(exc))
        finally:
            session.close()

    threads = [threading.Thread(target=act, args=(action,)) for action in ("complete_point", "skip_point")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results) == ["conflict", "success"]
    # With a second point still open after the winning thread's commit,
    # the session itself remains active (not completed), so the losing
    # thread's re-read of the row reaches apply_action's point-level
    # check and observes the first point already finalized.
    assert conflict_messages == ["Route session point is already finalized"]
    session_ids = [row[0] for row in pg_session.query(RouteSession.id).filter(RouteSession.id == state.session_id).all()]
    pg_session.query(RouteSessionPoint).filter(RouteSessionPoint.session_id.in_(session_ids)).delete(synchronize_session=False)
    pg_session.query(RouteSession).filter(RouteSession.id.in_(session_ids)).delete(synchronize_session=False)
    pg_session.query(Route).filter(Route.city_id == pg_city.id).delete(synchronize_session=False)
    pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id == issued.route_id).delete()
    pg_session.commit()
