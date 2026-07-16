"""Immutable CityAdminImportJob lifecycle regression coverage.

Production evidence this guards against: Job #1 (almaty) ended up
status="queued" while carrying started_at/finished_at/exit_code=1 from an
earlier, unrelated worker run — a terminal row had been reset back to
queued and reused. The fix (services/admin_city_import_job_service.py):
every launch/retry inserts a brand-new row; an existing row is never reset
back to queued/running once terminal; retries point at the row they
replace via previous_job_id."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

import pytest
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import (
    DuplicateActiveJobError,
    InvalidJobTransitionError,
    _transition,
    queue_city_import_job,
    retry_import_job,
    run_city_import_job,
)
from services.admin_city_import_tasks import run_queued_import_jobs
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_terminal_job_cannot_be_requeued_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="terminal-no-requeue-city")
    job = CityAdminImportJob(city_id=city.id, status="success", started_at=datetime.utcnow(), finished_at=datetime.utcnow())
    db_session.add(job)
    db_session.commit()

    with pytest.raises(InvalidJobTransitionError):
        _transition(db_session, job, "queued")
    with pytest.raises(InvalidJobTransitionError):
        _transition(db_session, job, "running")
    assert job.status == "success"


def test_new_launch_creates_new_row_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="new-launch-new-row-city")
    first = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    first.status = "failed"
    first.finished_at = datetime.utcnow()
    first.started_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.commit()

    second = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    assert second.id != first.id
    assert second.previous_job_id == first.id
    assert second.status == "queued"
    # first row is untouched
    db_session.refresh(first)
    assert first.status == "failed"


def test_retry_creates_new_row_with_previous_job_id_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="retry-new-row-city")
    original = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    original.status = "success_with_warnings"
    original.finished_at = datetime.utcnow()
    original.started_at = datetime.utcnow() - timedelta(minutes=3)
    db_session.commit()

    retried = retry_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    assert retried.id != original.id
    assert retried.previous_job_id == original.id
    assert retried.status == "queued"
    assert retried.started_at is None
    assert retried.finished_at is None


def test_concurrent_enqueue_has_one_active_winner_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="concurrent-enqueue-city")
    winner = queue_city_import_job(db_session, city_id=city.id, actor_id="first")
    db_session.commit()

    with pytest.raises(DuplicateActiveJobError) as exc_info:
        queue_city_import_job(db_session, city_id=city.id, actor_id="second")

    assert exc_info.value.job_id == winner.id
    assert exc_info.value.job_status == "queued"
    active_count = (
        db_session.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city.id, CityAdminImportJob.status.in_(("queued", "running")))
        .count()
    )
    assert active_count == 1


def test_claim_ignores_previously_started_queued_rows_new(db_session: Session, city_factory: Callable[..., Any], monkeypatch) -> None:
    """The production Job #1 shape: status="queued" but started_at/finished_at
    already set (a legacy-corrupted row). The worker claim query must not
    pick it up."""
    city = city_factory(slug="claim-ignores-corrupted-city")
    corrupted = CityAdminImportJob(
        city_id=city.id,
        status="queued",
        source="admin_city_import",
        started_at=datetime.utcnow() - timedelta(hours=1),
        finished_at=datetime.utcnow() - timedelta(minutes=30),
        last_error="exit_code=1",
    )
    db_session.add(corrupted)
    db_session.commit()

    monkeypatch.setattr("services.admin_city_import_tasks.SessionLocal", lambda: _SessionContext(db_session))
    result = run_queued_import_jobs(limit=5)

    assert result["processed"] == 0
    assert result["failed"] == 0
    db_session.refresh(corrupted)
    assert corrupted.status == "queued"
    assert corrupted.started_at is not None


def test_two_worker_runs_never_share_timeline_or_counters_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="separate-timelines-city")
    job1 = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    job1.status = "failed"
    job1.finished_at = datetime.utcnow()
    job1.started_at = datetime.utcnow() - timedelta(minutes=10)
    job1.places_found = 40
    job1.places_saved = 20
    db_session.commit()

    job2 = retry_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    assert job2.places_found == 0
    assert job2.places_saved == 0
    assert job2.started_at is None

    diag1 = build_import_job_diagnostic(db_session, job_id=job1.id)
    diag2 = build_import_job_diagnostic(db_session, job_id=job2.id)
    assert diag1["job_id"] != diag2["job_id"]
    assert diag2["previous_job_id"] == job1.id
    assert diag1["previous_job_id"] is None


def test_no_job_worker_run_mutates_nothing_new(db_session: Session, monkeypatch) -> None:
    before = db_session.query(CityAdminImportJob).count()
    monkeypatch.setattr("services.admin_city_import_tasks.SessionLocal", lambda: _SessionContext(db_session))
    result = run_queued_import_jobs(limit=5)
    after = db_session.query(CityAdminImportJob).count()

    assert result["processed"] == 0
    assert before == after


def test_diagnostics_for_job_n_exclude_job_n_minus_1_events_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    from services.admin_city_import_log import log_import_event

    city = city_factory(slug="diagnostic-isolation-city")
    job1 = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    log_import_event(db_session, event="import_job_started", city_slug=city.slug, actor_id="tester", message="job1 started", details={}, job_id=job1.id)
    job1.status = "failed"
    job1.finished_at = datetime.utcnow()
    job1.started_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    job2 = retry_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    log_import_event(db_session, event="import_job_started", city_slug=city.slug, actor_id="tester", message="job2 started", details={}, job_id=job2.id)
    db_session.commit()

    diag2 = build_import_job_diagnostic(db_session, job_id=job2.id)
    messages = [event["summary"] for event in diag2["timeline"]]
    assert "job1 started" not in messages
    assert "job2 started" in messages


def test_retry_chain_diagnostics_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="retry-chain-diagnostic-city")
    job1 = queue_city_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    job1.status = "failed"
    job1.finished_at = datetime.utcnow()
    job1.started_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.commit()

    job2 = retry_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()
    job2.status = "failed"
    job2.finished_at = datetime.utcnow()
    job2.started_at = datetime.utcnow() - timedelta(minutes=3)
    db_session.commit()

    job3 = retry_import_job(db_session, city_id=city.id, actor_id="tester")
    db_session.commit()

    diag = build_import_job_diagnostic(db_session, job_id=job3.id)
    assert diag["previous_job_id"] == job2.id
    chain_ids = [entry["job_id"] for entry in diag["retry_chain"]]
    assert chain_ids == [job1.id, job2.id]


def test_legacy_corrupted_row_detection_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="legacy-corrupted-detection-city")
    corrupted = CityAdminImportJob(
        city_id=city.id,
        status="queued",
        source="admin_city_import",
        started_at=datetime.utcnow() - timedelta(hours=1),
        finished_at=datetime.utcnow() - timedelta(minutes=30),
    )
    db_session.add(corrupted)
    db_session.commit()

    diag = build_import_job_diagnostic(db_session, job_id=corrupted.id)
    assert diag["legacy_corrupted"] is True
    assert "started_at" in diag["legacy_corrupted_reason"]

    clean = CityAdminImportJob(city_id=city.id, status="failed", started_at=datetime.utcnow() - timedelta(minutes=5), finished_at=datetime.utcnow())
    db_session.add(clean)
    db_session.commit()
    diag_clean = build_import_job_diagnostic(db_session, job_id=clean.id)
    assert diag_clean["legacy_corrupted"] is False


def test_production_job1_reproduction_new(db_session: Session, city_factory: Callable[..., Any], monkeypatch) -> None:
    """Reproduces the exact reported Job #1 (almaty) shape: status=queued,
    but started_at/finished_at set from an earlier run, mixed history. The
    worker must refuse to claim it, and the diagnostic must label it
    legacy_corrupted rather than presenting it as a normal queued job."""
    city = city_factory(slug="almaty")
    job1 = CityAdminImportJob(
        id=1,
        city_id=city.id,
        status="queued",
        source="admin_city_import",
        started_at=datetime.utcnow() - timedelta(hours=2),
        finished_at=datetime.utcnow() - timedelta(hours=1),
        last_error="exit_code=1",
        retry_count=3,
    )
    db_session.add(job1)
    db_session.commit()

    monkeypatch.setattr("services.admin_city_import_tasks.SessionLocal", lambda: _SessionContext(db_session))
    result = run_queued_import_jobs(limit=5)
    assert result["processed"] == 0

    diag = build_import_job_diagnostic(db_session, job_id=job1.id)
    assert diag["legacy_corrupted"] is True
    assert diag["status"] == "queued"

    from data.scripts.repair_import_job_lifecycle import _force_terminal, _flag_corrupted_jobs

    _flag_corrupted_jobs(db_session, apply_mode=True, actor_id="repair-test")
    db_session.refresh(job1)
    assert job1.lifecycle_flag == "legacy_corrupted"

    _force_terminal(db_session, job_id=job1.id, status="failed", actor_id="repair-test")
    db_session.refresh(job1)
    assert job1.status == "failed"

    retried = retry_import_job(db_session, city_id=city.id, actor_id="repair-test")
    db_session.commit()
    assert retried.previous_job_id == job1.id
    assert retried.status == "queued"
    assert retried.started_at is None
