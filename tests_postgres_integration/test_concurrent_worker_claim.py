"""Real concurrent-connection tests for job/scope claiming.

SQLite cannot exercise these: it has no real concurrent-writer row locking
model, so `FOR UPDATE SKIP LOCKED` and atomic `UPDATE ... WHERE` races are
indistinguishable from single-threaded execution there. These tests run
two genuinely separate PostgreSQL connections/transactions against the
same row concurrently and assert exactly one winner.
"""
from __future__ import annotations

import threading
from datetime import datetime

from sqlalchemy import and_

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.import_job_service import lock_scope, unlock_scope

from conftest import make_published_place, unique_slug


def test_for_update_skip_locked_gives_each_worker_a_distinct_job_new(pg_session, pg_city) -> None:
    """Two workers racing skip_locked against two queued jobs must each claim one.

    Schema allows only one active (queued/running) job per city, so the two
    jobs are seeded on distinct cities while workers claim from the shared set.
    """
    city_b = City(
        slug=unique_slug("pg-city-b"),
        name="PG Integration City B",
        is_active=True,
        launch_status="published",
    )
    pg_session.add(city_b)
    pg_session.commit()
    pg_session.refresh(city_b)

    job_a = CityAdminImportJob(city_id=pg_city.id, status="queued", source="admin_city_import")
    job_b = CityAdminImportJob(city_id=city_b.id, status="queued", source="admin_city_import")
    pg_session.add_all([job_a, job_b])
    pg_session.commit()
    pg_session.refresh(job_a)
    pg_session.refresh(job_b)
    job_ids = {int(job_a.id), int(job_b.id)}

    claimed_ids: list[int] = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def worker() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            job = (
                session.query(CityAdminImportJob)
                .filter(
                    CityAdminImportJob.id.in_(job_ids),
                    CityAdminImportJob.status == "queued",
                )
                .order_by(CityAdminImportJob.id.asc())
                .with_for_update(skip_locked=True)
                .first()
            )
            if job is not None:
                job.status = "running"
                session.commit()
                with lock:
                    claimed_ids.append(int(job.id))
            else:
                session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(claimed_ids) == sorted(job_ids)
    assert len(set(claimed_ids)) == 2

    pg_session.query(CityAdminImportJob).filter(CityAdminImportJob.id.in_(job_ids)).delete(
        synchronize_session=False
    )
    pg_session.query(City).filter(City.id == city_b.id).delete(synchronize_session=False)
    pg_session.commit()


def test_for_update_skip_locked_never_double_claims_a_single_job_new(pg_session, pg_city) -> None:
    """Two workers racing for the SAME single queued job: exactly one must
    win, the other must see no claimable rows via skip_locked."""
    job = CityAdminImportJob(city_id=pg_city.id, status="queued", source="admin_city_import")
    pg_session.add(job)
    pg_session.commit()
    pg_session.refresh(job)

    results: list[bool] = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def worker() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            claimed = (
                session.query(CityAdminImportJob)
                .filter(CityAdminImportJob.id == job.id, CityAdminImportJob.status == "queued")
                .with_for_update(skip_locked=True)
                .first()
            )
            won = claimed is not None
            if won:
                claimed.status = "running"
            session.commit()
            with lock:
                results.append(won)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results) == [False, True]

    pg_session.refresh(job)
    assert job.status == "running"


def test_scope_lock_atomic_update_prevents_double_lock_new(pg_session, pg_city) -> None:
    """services/import_job_service.py::lock_scope uses an atomic
    UPDATE ... WHERE locked_at IS NULL — exactly one of two racing callers
    must observe updated == 1."""
    scope = CityImportScope(
        city_id=pg_city.id,
        code=unique_slug("scope"),
        name="PG scope lock race",
        enabled=True,
    )
    pg_session.add(scope)
    pg_session.commit()
    pg_session.refresh(scope)

    outcomes: list[bool] = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def racer() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            local_scope = session.query(CityImportScope).filter(CityImportScope.id == scope.id).one()
            acquired = lock_scope(session, local_scope, datetime.utcnow())
            with lock:
                outcomes.append(acquired)
        finally:
            session.close()

    threads = [threading.Thread(target=racer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(outcomes) == [False, True]

    pg_session.refresh(scope)
    assert scope.locked_at is not None
    unlock_scope(pg_session, scope)
