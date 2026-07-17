from __future__ import annotations

import threading
from datetime import datetime, timedelta

import pytest

from db.session import SessionLocal
from models.place import Place
from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.route_state_cleanup_service import cleanup_expired_route_states
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
                lat=float(place.lat),
                lng=float(place.lng),
                category=str(place.category),
                visit_minutes=20,
            )
        ],
    )


def test_admin_hide_cannot_commit_between_state_validation_and_revision_commit_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    previous = register_initial_route_state(pg_session, _state(place, pg_city.slug, unique_slug("evidence-lock")))
    pg_session.commit()

    evidence_locked = threading.Event()
    release_route = threading.Event()
    admin_done = threading.Event()
    order: list[str] = []
    errors: list[BaseException] = []

    def route_mutation() -> None:
        db = SessionLocal()
        try:
            registry = verify_current_route_state(db, previous, lock=True)
            advance_route_state(db, previous=previous, next_state=previous, registry=registry)
            evidence_locked.set()
            release_route.wait(timeout=5)
            db.commit()
            order.append("route")
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    def admin_hide() -> None:
        evidence_locked.wait(timeout=5)
        db = SessionLocal()
        try:
            row = db.get(Place, place.id)
            row.is_route_eligible = False
            db.commit()
            order.append("admin")
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()
            admin_done.set()

    route_thread = threading.Thread(target=route_mutation)
    admin_thread = threading.Thread(target=admin_hide)
    route_thread.start()
    admin_thread.start()
    assert evidence_locked.wait(timeout=5)
    assert not admin_done.wait(timeout=0.2)
    release_route.set()
    route_thread.join(timeout=10)
    admin_thread.join(timeout=10)

    assert not errors
    assert order == ["route", "admin"]
    pg_session.query(UserRouteStateRegistry).filter_by(route_id=previous.route_id).delete()
    pg_session.commit()


def test_admin_hide_that_commits_first_prevents_revision_issuance_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    previous = register_initial_route_state(pg_session, _state(place, pg_city.slug, unique_slug("evidence-reject")))
    pg_session.commit()

    admin = SessionLocal()
    try:
        row = admin.get(Place, place.id)
        row.is_route_eligible = False
        admin.commit()
    finally:
        admin.close()

    registry = verify_current_route_state(pg_session, previous, lock=True)
    with pytest.raises(UserRouteStateConflictError):
        advance_route_state(pg_session, previous=previous, next_state=previous, registry=registry)
    pg_session.rollback()
    pg_session.query(UserRouteStateRegistry).filter_by(route_id=previous.route_id).delete()
    pg_session.commit()


def test_cleanup_skips_registry_while_concurrent_renewal_holds_lock_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    previous = register_initial_route_state(pg_session, _state(place, pg_city.slug, unique_slug("cleanup-renew")))
    registry = pg_session.get(UserRouteStateRegistry, previous.route_id)
    assert registry is not None
    registry.expires_at = datetime.utcnow() - timedelta(seconds=1)
    pg_session.commit()

    renewal_locked = threading.Event()
    release_renewal = threading.Event()
    errors: list[BaseException] = []

    def renew() -> None:
        db = SessionLocal()
        try:
            row = (
                db.query(UserRouteStateRegistry)
                .filter(UserRouteStateRegistry.route_id == previous.route_id)
                .with_for_update()
                .one()
            )
            row.expires_at = datetime.utcnow() + timedelta(hours=1)
            renewal_locked.set()
            release_renewal.wait(timeout=5)
            db.commit()
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    thread = threading.Thread(target=renew)
    thread.start()
    assert renewal_locked.wait(timeout=5)

    cleanup_db = SessionLocal()
    try:
        deleted = cleanup_expired_route_states(cleanup_db, limit=10)
        cleanup_db.commit()
    finally:
        cleanup_db.close()

    assert deleted == 0
    release_renewal.set()
    thread.join(timeout=10)
    assert not errors

    pg_session.expire_all()
    remaining = pg_session.get(UserRouteStateRegistry, previous.route_id)
    assert remaining is not None
    assert remaining.expires_at > datetime.utcnow()
    pg_session.delete(remaining)
    pg_session.commit()


def test_cleanup_deletes_expired_state_before_mutation_and_state_cannot_resurrect_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    previous = register_initial_route_state(pg_session, _state(place, pg_city.slug, unique_slug("cleanup-wins")))
    registry = pg_session.get(UserRouteStateRegistry, previous.route_id)
    assert registry is not None
    registry.expires_at = datetime.utcnow() - timedelta(seconds=1)
    pg_session.commit()

    cleanup_db = SessionLocal()
    try:
        assert cleanup_expired_route_states(cleanup_db, limit=10) == 1
        cleanup_db.commit()
    finally:
        cleanup_db.close()

    pg_session.expire_all()
    with pytest.raises(UserRouteStateConflictError):
        verify_current_route_state(pg_session, previous, lock=True)
    pg_session.rollback()


def test_two_cleanup_workers_delete_each_expired_row_once_new(pg_session, pg_city, pg_category) -> None:
    places = [make_published_place(pg_session, city=pg_city, category=pg_category) for _ in range(4)]
    states = [
        register_initial_route_state(pg_session, _state(place, pg_city.slug, unique_slug(f"cleanup-worker-{index}")))
        for index, place in enumerate(places)
    ]
    route_ids = [state.route_id for state in states]
    pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id.in_(route_ids)).update(
        {UserRouteStateRegistry.expires_at: datetime.utcnow() - timedelta(seconds=1)},
        synchronize_session=False,
    )
    pg_session.commit()

    barrier = threading.Barrier(2)
    deleted_counts: list[int] = []
    errors: list[BaseException] = []

    def cleanup_worker() -> None:
        db = SessionLocal()
        try:
            barrier.wait(timeout=5)
            deleted_counts.append(cleanup_expired_route_states(db, limit=2))
            db.commit()
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    first = threading.Thread(target=cleanup_worker)
    second = threading.Thread(target=cleanup_worker)
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not errors
    assert sum(deleted_counts) == 4
    assert pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id.in_(route_ids)).count() == 0
