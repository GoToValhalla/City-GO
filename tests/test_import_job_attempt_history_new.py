"""Retry/attempt history contract: CityAdminImportJob reuses one row across
retries (status/last_error/started_at/finished_at all overwritten in place,
retry_count incremented) — but the durable, append-only system_logs table is
never overwritten. build_import_job_diagnostic's "attempts" field segments
that raw timeline into distinct start/end/result records per retry, so a
worker crash followed by a later successful/failed retry stays
distinguishable and no earlier terminal result is silently hidden by a
later one."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic
from services.system_log_service import write_system_log


def _create_job(db: Session, *, city_id: int, **kwargs: Any) -> CityAdminImportJob:
    defaults: dict[str, Any] = dict(city_id=city_id, status="queued", source="admin_city_import", current_step="created")
    defaults.update(kwargs)
    job = CityAdminImportJob(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _log(db: Session, *, job_id: int, event: str, level: str = "info", at: datetime, **details: Any) -> None:
    row = write_system_log(
        db, level=level, module="import_worker", message=event, details={"event": event, "job_id": job_id, **details},
        request_id=str(job_id), commit=True,
    )
    row.created_at = at
    db.commit()


def test_terminal_evidence_remains_available_after_retry_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A job that failed once and was later retried to success must still
    expose the FIRST failure's evidence — retry_count going up must not
    erase it from the durable timeline."""
    city = city_factory(slug="retry-evidence-city")
    job = _create_job(db_session, city_id=city.id, status="success", current_step="ready_for_review", retry_count=1)
    t0 = datetime.utcnow() - timedelta(hours=1)
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0)
    _log(db_session, job_id=job.id, event="worker_job_failed", level="error", at=t0 + timedelta(minutes=1), error="boom")
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0 + timedelta(minutes=5))
    _log(db_session, job_id=job.id, event="worker_job_finished", at=t0 + timedelta(minutes=10))

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    # CityAdminImportJob's own row only reflects the LATEST state...
    assert diagnostic["status"] == "success"
    # ...but the raw timeline still contains the earlier failure event.
    failure_events = [e for e in diagnostic["timeline"] if e["type"] == "failed"]
    assert len(failure_events) == 1
    assert failure_events[0]["payload"]["error"] == "boom"


def test_retry_attempt_has_own_start_end_result_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="retry-attempt-boundaries-city")
    job = _create_job(db_session, city_id=city.id, status="failed", current_step="error", retry_count=1)
    t0 = datetime.utcnow() - timedelta(hours=1)
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0)
    _log(db_session, job_id=job.id, event="worker_job_failed", level="error", at=t0 + timedelta(minutes=1))
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0 + timedelta(minutes=5))
    _log(db_session, job_id=job.id, event="worker_job_failed", level="error", at=t0 + timedelta(minutes=6))

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    attempts = diagnostic["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["attempt_number"] == 1
    assert attempts[0]["result"] == "worker_job_failed"
    assert attempts[0]["started_at"] < attempts[0]["ended_at"]
    assert attempts[1]["attempt_number"] == 2
    assert attempts[1]["result"] == "worker_job_failed"
    assert attempts[0]["ended_at"] < attempts[1]["started_at"]


def test_worker_crash_and_subsequent_retry_are_distinguishable_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A worker that crashes silently (no worker_job_failed/finished/stalled
    event at all — see Defect #6 from the E2E rehearsal, where a SystemExit
    used to kill the worker before it could log a terminal event) must be
    distinguishable from a later, real retry — not silently merged into one
    attempt or dropped."""
    city = city_factory(slug="worker-crash-distinguishable-city")
    job = _create_job(db_session, city_id=city.id, status="failed", current_step="error", retry_count=1)
    t0 = datetime.utcnow() - timedelta(hours=1)
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0)
    # No terminal event for this attempt — the worker died silently.
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0 + timedelta(minutes=30))
    _log(db_session, job_id=job.id, event="worker_job_failed", level="error", at=t0 + timedelta(minutes=31))

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    attempts = diagnostic["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["result"] == "worker_crashed_no_terminal_event"
    assert attempts[1]["result"] == "worker_job_failed"


def test_no_status_rewind_hides_earlier_failure_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Regression for the E2E rehearsal's real retry_count=5 job: the job
    row's own status ends up 'failed' (the latest attempt's honest result),
    but earlier attempts (e.g. a genuine stall) must remain visible in the
    timeline/attempts — not overwritten into invisibility."""
    city = city_factory(slug="no-status-rewind-city")
    job = _create_job(db_session, city_id=city.id, status="failed", current_step="error", retry_count=2)
    t0 = datetime.utcnow() - timedelta(hours=1)
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0)
    _log(db_session, job_id=job.id, event="worker_job_stalled", level="error", at=t0 + timedelta(minutes=30))
    _log(db_session, job_id=job.id, event="worker_job_claimed", at=t0 + timedelta(minutes=35))
    _log(db_session, job_id=job.id, event="worker_job_failed", level="error", at=t0 + timedelta(minutes=36))

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    stalled_events = [e for e in diagnostic["timeline"] if e["type"] == "stalled"]
    assert len(stalled_events) == 1
    attempts = diagnostic["attempts"]
    assert attempts[0]["result"] == "worker_job_stalled"
    assert attempts[1]["result"] == "worker_job_failed"
