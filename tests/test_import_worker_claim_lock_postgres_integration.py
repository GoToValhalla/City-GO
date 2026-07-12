"""
Real-PostgreSQL concurrency proof for the import-worker claim query.

Uses two independent SQLAlchemy sessions against a real PostgreSQL server
(no SQLite, no mocking) to prove the exact mechanism reported for Job #9:

  - session A takes a raw `SELECT ... FOR UPDATE` lock on a queued job row
    and never commits/rolls back (simulating an abandoned/SIGKILLed worker
    connection);
  - session B runs the worker's own claim query
    (`FOR UPDATE SKIP LOCKED LIMIT 1`) and gets zero rows;
  - a lock-free `COUNT(*)` in the same moment still reports queued=1.

This distinguishes "queue is genuinely empty" from "queue is stuck behind a
lock" with real database behavior, not an assumption.

Requires a reachable PostgreSQL server and is opt-in, so default local/CI
runs (SQLite) are unaffected:

  RUN_IMPORT_WORKER_LOCK_INTEGRATION=1 \
  IMPORT_WORKER_LOCK_TEST_DATABASE_URL=postgresql+psycopg://user@127.0.0.1:5432/postgres \
  python3.11 -m pytest tests/test_import_worker_claim_lock_postgres_integration.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.base import Base
from models.city import City
from models.city_admin_import_job import CityAdminImportJob


def _integration_enabled() -> bool:
    return os.environ.get("RUN_IMPORT_WORKER_LOCK_INTEGRATION", "").strip() == "1"


def _test_database_url() -> str | None:
    return os.environ.get("IMPORT_WORKER_LOCK_TEST_DATABASE_URL", "").strip() or None


pytestmark = pytest.mark.skipif(
    not _integration_enabled() or not _test_database_url(),
    reason=(
        "Set RUN_IMPORT_WORKER_LOCK_INTEGRATION=1 and "
        "IMPORT_WORKER_LOCK_TEST_DATABASE_URL=postgresql+psycopg://... to run "
        "this real-PostgreSQL concurrency proof (see module docstring)."
    ),
)


@pytest.fixture
def pg_engine():
    admin_engine = create_engine(_test_database_url())
    db_name = f"citygo_lock_proof_{uuid.uuid4().hex[:12]}"
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    base_url = _test_database_url().rsplit("/", 1)[0]
    test_url = f"{base_url}/{db_name}"
    test_engine = create_engine(test_url)
    Base.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        test_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        admin_engine.dispose()


def _claim_query(session):
    return (
        session.query(CityAdminImportJob)
        .filter(CityAdminImportJob.status == "queued")
        .order_by(CityAdminImportJob.created_at.asc(), CityAdminImportJob.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
        .all()
    )


def test_skip_locked_returns_nothing_while_lock_free_count_sees_queued_job(pg_engine) -> None:
    """Proves the exact mechanism: a queued job locked by another session is
    invisible to the worker's SKIP LOCKED claim, while a plain COUNT(*)
    still truthfully reports it as queued."""
    Session = sessionmaker(bind=pg_engine)

    setup = Session()
    city = City(slug="lock-proof-city", name="Lock Proof City", country="Test")
    setup.add(city)
    setup.commit()
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    setup.add(job)
    setup.commit()
    job_id = job.id
    setup.close()

    # Session A: lock the row and deliberately never commit/rollback,
    # simulating an abandoned/SIGKILLed worker connection holding the lock.
    session_a = Session()
    session_a.execute(text("BEGIN"))
    locked_row = session_a.execute(
        text("SELECT id FROM city_admin_import_jobs WHERE id = :id FOR UPDATE"),
        {"id": job_id},
    ).fetchone()
    assert locked_row is not None

    try:
        # Session B: the worker's own exact claim query.
        session_b = Session()
        try:
            claimed = _claim_query(session_b)
            assert claimed == [], "SKIP LOCKED must return nothing while the row is locked"

            lock_free_count = (
                session_b.query(CityAdminImportJob)
                .filter(CityAdminImportJob.status == "queued")
                .count()
            )
            assert lock_free_count == 1, "a lock-free count must still see the job as queued"
        finally:
            session_b.rollback()
            session_b.close()
    finally:
        session_a.rollback()
        session_a.close()


def test_idle_in_transaction_timeout_releases_the_stuck_lock(pg_engine) -> None:
    """Proves the proposed fix: setting idle_in_transaction_session_timeout
    on the connection causes PostgreSQL to terminate an abandoned
    transaction on its own, releasing the lock without any application-level
    lock termination, direct row mutation, or change to SKIP LOCKED."""
    Session = sessionmaker(bind=pg_engine)

    setup = Session()
    city = City(slug="idle-timeout-city", name="Idle Timeout City", country="Test")
    setup.add(city)
    setup.commit()
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    setup.add(job)
    setup.commit()
    job_id = job.id
    setup.close()

    session_a = Session()
    session_a.execute(text("SET idle_in_transaction_session_timeout = 500"))
    session_a.execute(text("BEGIN"))
    locked_row = session_a.execute(
        text("SELECT id FROM city_admin_import_jobs WHERE id = :id FOR UPDATE"),
        {"id": job_id},
    ).fetchone()
    assert locked_row is not None

    import time

    time.sleep(1.0)  # exceed the 500ms idle_in_transaction_session_timeout

    session_b = Session()
    try:
        claimed = _claim_query(session_b)
        assert len(claimed) == 1
        assert claimed[0].id == job_id
    finally:
        session_b.rollback()
        session_b.close()

    with pytest.raises(Exception):
        session_a.execute(text("SELECT 1"))
    session_a.close()
