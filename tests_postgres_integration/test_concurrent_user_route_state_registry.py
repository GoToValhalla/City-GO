from __future__ import annotations

import threading

from db.session import SessionLocal
from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)
from tests_postgres_integration.conftest import make_published_place, unique_slug


def _state(place, city_slug: str, route_id: str) -> UserRouteState:
    return UserRouteState(
        route_id=route_id,
        revision=1,
        status="ready",
        context=UserRouteIntent(lat=float(place.lat), lng=float(place.lng), city_id=city_slug, time_budget_minutes=120),
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(
                place_id=str(place.id),
                city_slug=city_slug,
                position=1,
                title=place.title,
                address=place.address,
                lat=float(place.lat),
                lng=float(place.lng),
                category=str(place.category),
                visit_minutes=20,
            )
        ],
    )


def test_concurrent_initial_registration_is_one_idempotent_claim_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    route_id = unique_slug("registry-claim")
    state = _state(place, pg_city.slug, route_id)
    barrier = threading.Barrier(2)
    tokens: list[str] = []
    errors: list[BaseException] = []

    def run() -> None:
        db = SessionLocal()
        try:
            barrier.wait(timeout=5)
            issued = register_initial_route_state(db, state)
            db.commit()
            tokens.append(str(issued.state_token))
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=run), threading.Thread(target=run)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert len(tokens) == 2
    assert len(set(tokens)) == 1
    assert pg_session.query(UserRouteStateRegistry).filter_by(route_id=route_id).count() == 1
    pg_session.query(UserRouteStateRegistry).filter_by(route_id=route_id).delete()
    pg_session.commit()


def test_parallel_mutations_allow_exactly_one_revision_owner_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    route_id = unique_slug("registry-mutation")
    previous = register_initial_route_state(pg_session, _state(place, pg_city.slug, route_id))
    pg_session.commit()
    barrier = threading.Barrier(2)
    successes: list[int] = []
    conflicts: list[BaseException] = []

    def run(label: str) -> None:
        db = SessionLocal()
        try:
            barrier.wait(timeout=5)
            registry = verify_current_route_state(db, previous, lock=True)
            next_state = previous.model_copy(update={"warnings": [label], "has_warnings": True, "warning_count": 1})
            issued = advance_route_state(db, previous=previous, next_state=next_state, registry=registry)
            db.commit()
            successes.append(int(issued.revision))
        except UserRouteStateConflictError as exc:
            db.rollback()
            conflicts.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=run, args=("first",)), threading.Thread(target=run, args=("second",))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert successes == [2]
    assert len(conflicts) == 1
    row = pg_session.query(UserRouteStateRegistry).filter_by(route_id=route_id).one()
    assert row.revision == 2
    pg_session.delete(row)
    pg_session.commit()
