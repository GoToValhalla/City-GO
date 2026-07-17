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
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    route = _route(place, pg_city.slug, f"session-race-{place.id}")
    issued = register_initial_route_state(pg_session, route)
    state = UserRouteSessionService().start(pg_session, UserRouteSessionStartRequest(current_route=issued, user_id="pg-user"))
    pg_session.commit()
    start = threading.Barrier(2)
    results: list[str] = []

    def act(action: str) -> None:
        session = SessionLocal()
        try:
            start.wait(timeout=5)
            UserRouteSessionService().apply_action(session, state.session_id, UserRouteSessionActionRequest(action=action, place_id=str(place.id)))
            session.commit()
            results.append("success")
        except UserRouteSessionError:
            session.rollback()
            results.append("conflict")
        finally:
            session.close()

    threads = [threading.Thread(target=act, args=(action,)) for action in ("complete_point", "skip_point")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results) == ["conflict", "success"]
    session_ids = [row[0] for row in pg_session.query(RouteSession.id).filter(RouteSession.id == state.session_id).all()]
    pg_session.query(RouteSessionPoint).filter(RouteSessionPoint.session_id.in_(session_ids)).delete(synchronize_session=False)
    pg_session.query(RouteSession).filter(RouteSession.id.in_(session_ids)).delete(synchronize_session=False)
    pg_session.query(Route).filter(Route.city_id == pg_city.id).delete(synchronize_session=False)
    pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id == issued.route_id).delete()
    pg_session.commit()
