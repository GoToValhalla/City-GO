from __future__ import annotations

import os
import threading
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.city import City
from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.place_verification_mutation import transition_place_verification, verify_locked_place
from services.publication_state_writer import (
    REASON_ADMIN_HIDE,
    REASON_ADMIN_UNPUBLISH,
    transition_locked_places_publication,
)

POSTGRES_URL = os.getenv("CITYGO_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL or not POSTGRES_URL.startswith("postgresql"),
    reason="CITYGO_POSTGRES_TEST_URL is required for real PostgreSQL locking tests",
)


def _session_factory():
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed_two_places(factory) -> tuple[int, int, int]:
    suffix = uuid.uuid4().hex[:10]
    with factory() as db:
        city = City(
            name=f"Publication lock {suffix}",
            slug=f"publication-lock-{suffix}",
            country="Test",
            region="Test",
            timezone="UTC",
            center_lat=1.0,
            center_lng=1.0,
            is_active=True,
            launch_status="published",
        )
        db.add(city)
        db.flush()
        places = [
            Place(
                city_id=city.id,
                slug=f"publication-lock-{suffix}-{index}",
                title=f"Place {index}",
                lat=1.0 + index,
                lng=1.0 + index,
                status="active",
                internal_status="active",
                lifecycle_status="active",
                is_active=True,
                is_published=True,
                is_visible_in_catalog=True,
                is_searchable=True,
                is_route_eligible=True,
                publication_status="published",
                publication_reason_code=None,
                publication_reason_details={},
                verification_status="unverified",
                existence_confidence_score=0,
                existence_confidence_level="unknown",
            )
            for index in (1, 2)
        ]
        db.add_all(places)
        db.commit()
        return int(city.id), int(places[0].id), int(places[1].id)


def _cleanup(factory, city_id: int) -> None:
    with factory() as db:
        place_ids = [row[0] for row in db.query(Place.id).filter(Place.city_id == city_id).all()]
        if place_ids:
            db.query(PlacePublicationTransition).filter(
                PlacePublicationTransition.place_id.in_(place_ids)
            ).delete(synchronize_session=False)
            db.query(Place).filter(Place.id.in_(place_ids)).delete(synchronize_session=False)
        db.query(City).filter(City.id == city_id).delete(synchronize_session=False)
        db.commit()


def _run_bulk_transition(
    factory,
    place_ids: tuple[int, int],
    *,
    reason_code: str,
    to_status: str,
    barrier: threading.Barrier,
    errors: list[BaseException],
) -> None:
    try:
        with factory() as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            barrier.wait(timeout=10)
            places = (
                db.query(Place)
                .filter(Place.id.in_(place_ids))
                .order_by(Place.id.asc())
                .with_for_update()
                .populate_existing()
                .all()
            )
            transition_locked_places_publication(
                db,
                places,
                to_status=to_status,
                reason_code=reason_code,
                actor="postgres-concurrency-test",
                source="postgres_integration",
                reason_details={"thread": threading.current_thread().name},
            )
            db.commit()
    except BaseException as exc:  # noqa: BLE001 - thread errors are asserted by parent
        errors.append(exc)


def test_deterministic_bulk_lock_order_prevents_deadlock() -> None:
    engine, factory = _session_factory()
    city_id, first_id, second_id = _seed_two_places(factory)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    try:
        threads = [
            threading.Thread(
                target=_run_bulk_transition,
                name="hide",
                args=(factory, (first_id, second_id)),
                kwargs={
                    "reason_code": REASON_ADMIN_HIDE,
                    "to_status": "hidden",
                    "barrier": barrier,
                    "errors": errors,
                },
            ),
            threading.Thread(
                target=_run_bulk_transition,
                name="unpublish",
                args=(factory, (second_id, first_id)),
                kwargs={
                    "reason_code": REASON_ADMIN_UNPUBLISH,
                    "to_status": "unpublished",
                    "barrier": barrier,
                    "errors": errors,
                },
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        with factory() as db:
            transitions = (
                db.query(PlacePublicationTransition)
                .filter(PlacePublicationTransition.place_id.in_((first_id, second_id)))
                .all()
            )
            assert len(transitions) == 4
            for place in db.query(Place).filter(Place.id.in_((first_id, second_id))).all():
                assert place.publication_status in {"hidden", "unpublished"}
                assert place.publication_reason_code in {REASON_ADMIN_HIDE, REASON_ADMIN_UNPUBLISH}
    finally:
        _cleanup(factory, city_id)
        engine.dispose()


def test_writer_flush_is_rolled_back_with_caller_transaction() -> None:
    engine, factory = _session_factory()
    city_id, first_id, _ = _seed_two_places(factory)
    try:
        with factory() as db:
            place = db.query(Place).filter(Place.id == first_id).with_for_update().one()
            transition_locked_places_publication(
                db,
                [place],
                to_status="hidden",
                reason_code=REASON_ADMIN_HIDE,
                actor="postgres-rollback-test",
                source="postgres_integration",
            )
            db.rollback()

        with factory() as db:
            place = db.get(Place, first_id)
            assert place is not None
            assert place.publication_status == "published"
            assert place.publication_reason_code is None
            assert (
                db.query(PlacePublicationTransition)
                .filter(PlacePublicationTransition.place_id == first_id)
                .count()
                == 0
            )
    finally:
        _cleanup(factory, city_id)
        engine.dispose()


def test_stale_verify_cannot_downgrade_concurrent_trusted() -> None:
    engine, factory = _session_factory()
    city_id, first_id, _ = _seed_two_places(factory)
    session_a = factory()
    try:
        stale = session_a.get(Place, first_id)
        assert stale is not None

        with factory() as session_b:
            current = session_b.query(Place).filter(Place.id == first_id).with_for_update().one()
            transition_place_verification(
                session_b,
                current,
                to_status="trusted",
                actor="trusted-policy",
                verification_source="official_site",
                verification_method="trusted_source",
                confidence_score=100,
                confidence_level="high",
                lock_place=False,
            )
            session_b.commit()

        changed = verify_locked_place(
            session_a,
            stale,
            actor="ordinary-admin",
            verification_status="verified",
        )
        session_a.commit()
        assert changed is False

        with factory() as verify_db:
            current = verify_db.get(Place, first_id)
            assert current is not None
            assert current.verification_status == "trusted"
            assert current.existence_confidence_score == 100
            assert current.verification_source == "official_site"
            assert current.verification_method == "trusted_source"
            assert current.verified_by == "trusted-policy"
    finally:
        session_a.close()
        _cleanup(factory, city_id)
        engine.dispose()
