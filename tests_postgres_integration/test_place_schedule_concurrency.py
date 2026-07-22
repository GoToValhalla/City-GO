"""Real PostgreSQL proof that write_catalog_schedule() cannot produce a
duplicate (place_id, weekday) row under a genuine concurrent race, and that
the uq_place_schedules_place_weekday unique index (migrations/versions/
e2c4b6a8d0f3_place_schedule_place_weekday_uniqueness.py) rejects a
duplicate at the database level. Uses two real threads with independent
SessionLocal() connections and a threading.Barrier, matching the pattern
in tests_postgres_integration/test_concurrent_user_route_state_registry.py
-- this is NOT a sequential same-session call.
"""
from __future__ import annotations

import threading
from datetime import time

from sqlalchemy.exc import IntegrityError

from db.session import SessionLocal
from models.place_schedule import PlaceSchedule
from services.stage6_contracts.catalog_entities import CatalogScheduleWrite, write_catalog_schedule
from tests_postgres_integration.conftest import make_published_place


def test_concurrent_write_catalog_schedule_race_produces_no_duplicate_row_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    place_id = int(place.id)
    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def act(hour: int) -> None:
        db = SessionLocal()
        try:
            barrier.wait(timeout=5)
            write_catalog_schedule(
                db,
                CatalogScheduleWrite(
                    place_id=place_id, weekday="mon",
                    open_time=time(hour, 0), close_time=time(hour + 8, 0),
                ),
            )
            db.commit()
            results.append("success")
        except BaseException as exc:
            db.rollback()
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=act, args=(9,)), threading.Thread(target=act, args=(10,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    # Both concurrent writers must succeed -- the whole point of
    # INSERT ... ON CONFLICT DO UPDATE is that neither side ever needs to
    # observe a unique-violation; the loser's insert atomically becomes an
    # update instead.
    assert not errors
    assert results == ["success", "success"]

    rows = pg_session.query(PlaceSchedule).filter(
        PlaceSchedule.place_id == place_id, PlaceSchedule.weekday == "mon",
    ).all()
    assert len(rows) == 1
    pg_session.query(PlaceSchedule).filter(PlaceSchedule.place_id == place_id).delete()
    pg_session.commit()


def test_database_unique_index_rejects_a_raw_duplicate_row_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    pg_session.add(PlaceSchedule(place_id=place.id, weekday="tue"))
    pg_session.commit()

    pg_session.add(PlaceSchedule(place_id=place.id, weekday="tue"))
    try:
        pg_session.commit()
        raise AssertionError("expected IntegrityError from uq_place_schedules_place_weekday")
    except IntegrityError:
        pg_session.rollback()

    rows = pg_session.query(PlaceSchedule).filter(
        PlaceSchedule.place_id == place.id, PlaceSchedule.weekday == "tue",
    ).all()
    assert len(rows) == 1
    pg_session.query(PlaceSchedule).filter(PlaceSchedule.place_id == place.id).delete()
    pg_session.commit()
