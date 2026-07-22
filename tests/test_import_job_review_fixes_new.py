"""Regression coverage for the 4 blockers found by independent code review
of commit 968e54c7 (the immutable import-job lifecycle fix):

1. Atomic worker claim: claim_queued_job() transitions queued -> running,
   sets started_at/claimed_by, and logs worker_job_claimed all under one
   row lock/commit — a second claim attempt on the same row must fail.
2. Concurrent enqueue: _enqueue_job() locks the city row so two concurrent
   enqueue attempts (even with no pre-existing active row) never both
   insert; a second layer (the partial unique index + IntegrityError
   handling) catches anything that slips past that.
3. No terminal -> running mutation: run_city_import_job's internal phases
   (run_enrichment_pipeline, run_foundation_pipeline) never write
   job.status directly — see test_import_job_status_assignment_ast_new.py
   for the repository-wide AST guard; this file adds a runtime check that
   job.status stays "running" throughout a real call.
4. No background/CLI claim bypass: run_import_job_background and friends
   must claim their job_id before running, and _resolve_run_job must
   reject a call made without an explicit, already-running job_id.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import (
    DuplicateActiveJobError,
    _resolve_run_job,
    claim_queued_job,
    queue_city_import_job,
    run_city_import_job,
)
from services.admin_city_import_tasks import run_queued_import_jobs


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


# --- 1. Atomic worker claim -------------------------------------------------


def test_claim_queued_job_transitions_and_sets_fields_atomically_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="claim-atomic-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    claimed = claim_queued_job(db_session, job_id=job.id, worker_id="worker-1", actor_id="tester")

    assert claimed.status == "running"
    assert claimed.started_at is not None
    assert claimed.claimed_by == "worker-1"
    from services.system_log_service import list_system_logs
    logs, _ = list_system_logs(db_session, module="import_worker", request_id=str(job.id), sort="asc", limit=50)
    events = [str((row.details or {}).get("event")) for row in logs]
    assert "worker_job_claimed" in events


def test_second_claim_attempt_on_same_job_fails_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="claim-second-attempt-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    first = claim_queued_job(db_session, job_id=job.id, worker_id="worker-1", actor_id="tester")
    assert first.status == "running"

    with pytest.raises(ValueError, match="уже не в состоянии queued"):
        claim_queued_job(db_session, job_id=job.id, worker_id="worker-2", actor_id="tester")


def test_two_concurrent_workers_never_claim_the_same_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Simulates two workers racing for one queued row: only one call to
    claim_queued_job succeeds; the second sees status != "queued" and
    raises, exactly like run_queued_import_jobs's own except ValueError
    handling (skip and move on) expects."""
    city = city_factory(slug="claim-two-workers-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    results: list[bool] = []
    for worker_id in ("worker-a", "worker-b"):
        try:
            claim_queued_job(db_session, job_id=job.id, worker_id=worker_id, actor_id="tester")
            results.append(True)
        except ValueError:
            results.append(False)

    assert results == [True, False]
    db_session.refresh(job)
    assert job.claimed_by == "worker-a"


def test_runner_rejects_missing_job_id_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="runner-missing-job-id-city")
    with pytest.raises(ValueError, match="job_id обязателен"):
        _resolve_run_job(db_session, city_id=city.id, job_id=None)


def test_runner_rejects_queued_status_not_yet_claimed_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A runner must never accept a job_id whose row is still "queued" —
    it must have gone through claim_queued_job (status="running") first."""
    city = city_factory(slug="runner-rejects-queued-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    with pytest.raises(ValueError, match="не в статусе running"):
        _resolve_run_job(db_session, city_id=city.id, job_id=job.id)


def test_worker_claim_query_ignores_already_running_job_new(db_session: Session, city_factory: Callable[..., Any], monkeypatch) -> None:
    """run_queued_import_jobs's claim query filters status == "queued" —
    a job already running (claimed by someone else) must never be
    re-claimed by a second worker pass."""
    city = city_factory(slug="claim-ignores-running-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    claim_queued_job(db_session, job_id=job.id, worker_id="worker-1", actor_id="tester")

    monkeypatch.setattr("services.admin_city_import_tasks.SessionLocal", lambda: _SessionContext(db_session))
    result = run_queued_import_jobs(limit=5)

    assert result["processed"] == 0
    db_session.refresh(job)
    assert job.claimed_by == "worker-1"


# --- 2. Concurrent enqueue serialization ------------------------------------


def test_concurrent_enqueue_two_independent_sessions_one_winner_new(engine, city_factory: Callable[..., Any]) -> None:
    """Uses two INDEPENDENT sessions/transactions (not one shared session)
    against the same underlying test engine (StaticPool sqlite, shared
    connection), matching the review's explicit requirement: 'test with
    two independent sessions/transactions, not one shared session.'"""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    setup_db = Session()
    try:
        city = City(name="Concurrent Enqueue City", slug="concurrent-enqueue-two-sessions", country="Россия", is_active=True, launch_status="published")
        setup_db.add(city)
        setup_db.commit()
        city_id = city.id
    finally:
        setup_db.close()

    outcomes: list[str] = []
    db_a, db_b = Session(), Session()
    try:
        for db in (db_a, db_b):
            try:
                job = queue_city_import_job(db, city_id=city_id, actor_id="tester")
                db.commit()
                outcomes.append(f"created:{job.id}")
            except DuplicateActiveJobError as exc:
                db.rollback()
                outcomes.append(f"duplicate:{exc.job_id}")
    finally:
        db_a.close()
        db_b.close()

    created = [o for o in outcomes if o.startswith("created:")]
    duplicates = [o for o in outcomes if o.startswith("duplicate:")]
    assert len(created) == 1
    assert len(duplicates) == 1
    winner_id = int(created[0].split(":")[1])
    assert int(duplicates[0].split(":")[1]) == winner_id

    verify_db = Session()
    try:
        active_count = (
            verify_db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.city_id == city_id, CityAdminImportJob.status.in_(("queued", "running")))
            .count()
        )
        assert active_count == 1
    finally:
        verify_db.close()

    # This test uses its own sessions committing directly against the
    # session-scoped `engine` fixture (deliberately, to get two genuinely
    # independent transactions) — unlike db_session, nothing rolls this
    # back automatically, so it must clean up after itself or these rows
    # leak into every later test's global job/city counts for the rest of
    # the run.
    cleanup_db = Session()
    try:
        cleanup_db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city_id).delete()
        cleanup_db.query(City).filter(City.id == city_id).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()


def test_enqueue_integrity_error_path_raises_truthful_duplicate_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """If a row somehow reaches the INSERT without going through the
    active-row check (simulated here by patching the check away), the
    partial unique index's IntegrityError must still be caught and
    translated into a truthful DuplicateActiveJobError — never an
    unhandled crash."""
    city = city_factory(slug="enqueue-integrity-error-city")
    existing = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    with patch("services.admin_city_import_job_service._active_job", return_value=None):
        with pytest.raises(DuplicateActiveJobError) as exc_info:
            queue_city_import_job(db_session, city_id=city.id, actor_id="tester")

    assert exc_info.value.job_id == existing.id


# --- 3. No terminal -> running mutation --------------------------------------


def test_job_status_stays_running_throughout_run_city_import_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Every internal phase call inside run_city_import_job must leave
    job.status == "running" — only the final _transition at the very end
    may change it."""
    city = city_factory(slug="status-stays-running-city")
    job = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    claimed = claim_queued_job(db_session, job_id=job.id, worker_id="worker-1", actor_id="tester")
    assert claimed.status == "running"

    observed_statuses: list[str] = []

    def _fake_pipeline(db, *, job, city, actor_id, force=True, notify_completion=True):
        observed_statuses.append(job.status)
        return {"status": "success", "changed_place_ids": []}

    def _fake_foundation(db, city, job, actor_id, ids):
        observed_statuses.append(job.status)
        return {"failed": 0}

    with patch("services.admin_city_import_job_service.run_enrichment_pipeline", side_effect=_fake_pipeline), \
         patch("services.admin_city_import_job_service._foundation", side_effect=_fake_foundation):
        finished = run_city_import_job(db_session, city_id=city.id, actor_id="tester", job_id=claimed.id)

    assert observed_statuses == ["running", "running"]
    assert finished.status == "success"


def test_partial_success_phase_outcome_does_not_touch_job_status_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A sub-phase reporting partial_success/failed via its return dict
    must not itself terminalize the parent job — only the caller's single
    final _transition may."""
    from services.import_pipeline.runner import run_enrichment_pipeline

    city = city_factory(slug="phase-outcome-no-mutation-city")
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", started_at=datetime.utcnow())
    db_session.add(job)
    db_session.commit()

    with patch("services.import_pipeline.runner.run_osm_import_only", return_value={"results": [{"status": "failed", "scope": "tourist_core", "error": "boom"}]}), \
         patch("services.import_pipeline.runner.run_address_backfill", return_value={"checked": 0, "updated": 0, "errors": 0}), \
         patch("services.import_pipeline.runner.run_image_enrich", return_value={"scanned_places": 0, "created": 0, "failed": 0}), \
         patch("services.import_pipeline.runner.normalize_places_categories", return_value={"scanned": 0, "updated": 0}), \
         patch("services.import_pipeline.runner.compute_city_readiness", return_value={"readiness_score": 0}):
        from models.place import Place
        place = Place(city_id=city.id, slug="phase-outcome-place", title="Place", lat=1.0, lng=1.0, category="park")
        db_session.add(place)
        db_session.commit()
        results = run_enrichment_pipeline(db_session, job=job, city=city, actor_id="tester", notify_completion=False)

    assert results["status"] in {"partial_success", "success_with_warnings", "success"}
    assert job.status == "running"


# --- 4. No background/CLI claim bypass --------------------------------------
#
# F04: run_import_job_background (and its never-called siblings
# run_enrichment_job_background / run_all_cities_enrichment_background) were
# removed entirely rather than kept as a guarded bypass. Each claimed and
# executed a CityAdminImportJob directly from a FastAPI BackgroundTasks
# callback (or a raw function call) inside the API server process itself —
# a second, unauthorized execution path alongside the import worker that
# bypassed every worker guarantee (memory/runtime limits, lifecycle,
# ownership, observability, recovery). See
# tests/test_admin_router_no_background_execution_new.py for the
# regression coverage on the admin endpoint itself.


def test_no_background_execution_functions_remain_in_admin_city_import_tasks_new() -> None:
    """The three deleted functions must never be reintroduced under any
    name in this module — a fresh AttributeError here is the intended,
    permanent signal that someone tried to bring back an in-process
    execution path."""
    import services.admin_city_import_tasks as tasks_module

    for name in ("run_import_job_background", "run_enrichment_job_background", "run_all_cities_enrichment_background"):
        assert not hasattr(tasks_module, name), f"{name} must not exist — see F04 (BackgroundTasks execution bypass)"
