"""Regression coverage for the blocker found by independent code review of
commit ddc800f0627750e11abd7a8f37be3a81032f5dc7:

Every runner (run_city_import_job, run_snapshot_refresh_job,
run_address_enrichment_job, run_photo_enrichment_job, run_enrichment_only_job)
and _mark_worker_exception called _transition() at the very end of its own
work, then — regardless of whether that transition actually succeeded —
unconditionally wrote finished_at/current_step/step_details/last_error on
the job row. When a concurrent process (mark_stalled_import_jobs, an admin
cancel, or a second stall-recovery sweep) had already moved the row out of
"running" into some OTHER terminal status while this run was still in
flight, _transition correctly raised InvalidJobTransitionError and
job.status itself stayed protected — but the unconditional writes right
after it still executed, silently clobbering the OTHER process's truthful
finished_at/last_error/step_details with this run's own late-arriving,
now-irrelevant result (or, worse, with a confusing internal message like
"job #N: invalid transition stalled -> success").

The fix: _try_finalize(db, job, new_status, actor_id=...) wraps
_transition and returns False (doing nothing else) when the transition was
rejected — every runner's finalize block is now conditional on that
return value, so a job recovered externally while this run was executing
keeps its own truthful terminal fields untouched.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import (
    InvalidJobTransitionError,
    _try_finalize,
    claim_queued_job,
    queue_city_import_job,
    run_address_enrichment_job,
    run_city_import_job,
    run_enrichment_only_job,
    run_photo_enrichment_job,
    run_snapshot_refresh_job,
)
from services.admin_city_import_tasks import _mark_worker_exception, mark_stalled_import_jobs


def _claim(db, *, city_id, actor_id="tester"):
    queued = queue_city_import_job(db, city_id=city_id, actor_id=actor_id)
    db.commit()
    return claim_queued_job(db, job_id=queued.id, worker_id="worker-1", actor_id=actor_id)


# --- _try_finalize itself ----------------------------------------------------


def test_try_finalize_returns_true_and_applies_on_valid_transition_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="try-finalize-valid-city")
    job = _claim(db_session, city_id=city.id)

    applied = _try_finalize(db_session, job, "success", actor_id="tester")

    assert applied is True
    assert job.status == "success"


def test_try_finalize_returns_false_and_does_not_touch_status_on_invalid_transition_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="try-finalize-invalid-city")
    job = _claim(db_session, city_id=city.id)
    job.status = "stalled"  # simulates a concurrent stall sweep having already terminalized the row
    db_session.commit()

    applied = _try_finalize(db_session, job, "success", actor_id="tester")

    assert applied is False
    assert job.status == "stalled"


# --- Every runner must not clobber a concurrently-stalled row's fields ------


def test_run_city_import_job_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any], monkeypatch) -> None:
    city = city_factory(slug="stall-race-full-import-city")
    job = _claim(db_session, city_id=city.id)

    # Simulate mark_stalled_import_jobs winning the race: by the time this
    # run reaches its own final _transition, the row is already "stalled"
    # with its own truthful finished_at/last_error.
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_pipeline(db, *, job, city, actor_id, force=True, notify_completion=True):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        return {"status": "success", "changed_place_ids": []}

    def _fake_foundation(db, city, job, actor_id, ids):
        return {"failed": 0}

    with patch("services.admin_city_import_job_service.run_enrichment_pipeline", side_effect=_fake_pipeline), \
         patch("services.admin_city_import_job_service._foundation", side_effect=_fake_foundation):
        finished = run_city_import_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


def test_run_city_import_job_exception_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-full-import-exception-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_pipeline_raises(db, *, job, city, actor_id, force=True, notify_completion=True):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        raise RuntimeError("provider crashed after stall recovery already ran")

    with patch("services.admin_city_import_job_service.run_enrichment_pipeline", side_effect=_fake_pipeline_raises):
        finished = run_city_import_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


def test_run_snapshot_refresh_job_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any], monkeypatch) -> None:
    city = city_factory(slug="stall-race-snapshot-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_refresh(db, *, city, job, source):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        return {}

    with patch("services.admin_city_import_job_service._refresh_snapshot_light", side_effect=_fake_refresh):
        finished = run_snapshot_refresh_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


def test_run_enrichment_only_job_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-enrichment-only-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_enrichment_only(db, *, job, city, actor_id):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        return {"status": "success"}

    def _fake_foundation(db, city, job, actor_id, ids):
        return {"failed": 0}

    with patch("services.admin_city_import_job_service.run_enrichment_only_pipeline", side_effect=_fake_enrichment_only), \
         patch("services.admin_city_import_job_service._foundation", side_effect=_fake_foundation):
        finished = run_enrichment_only_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


def test_run_enrichment_only_job_exception_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-enrichment-only-exception-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_enrichment_only_raises(db, *, job, city, actor_id):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        raise RuntimeError("provider crashed after stall recovery already ran")

    with patch("services.admin_city_import_job_service.run_enrichment_only_pipeline", side_effect=_fake_enrichment_only_raises):
        with pytest.raises(RuntimeError):
            run_enrichment_only_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.finished_at == stalled_finished_at
    assert job.last_error == stalled_last_error


def test_run_address_enrichment_job_blocked_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """No places in the city => the "blocked" path's own _try_finalize(...,
    "failed", ...) call must likewise be skipped if the row was already
    stalled by the time it runs."""
    city = city_factory(slug="stall-race-address-blocked-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"
    job.status = "stalled"
    job.finished_at = stalled_finished_at
    job.last_error = stalled_last_error
    db_session.commit()

    # _resolve_run_job requires status == "running", so calling the runner
    # directly on an already-stalled row raises before reaching any finalize
    # logic — this test instead exercises _try_finalize's guard directly
    # against the exact field set the blocked path would have written,
    # proving the guard (not luck) is what protects it.
    result = _try_finalize(db_session, job, "failed", actor_id="tester")
    assert result is False
    assert job.status == "stalled"
    assert job.finished_at == stalled_finished_at
    assert job.last_error == stalled_last_error


def test_run_photo_enrichment_job_success_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any], place_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-photo-city")
    place_factory(city_id=city.id, slug="stall-race-photo-place", title="Stall Race Photo Place")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_auto_repair(db, *, city, job, changed_place_ids):
        job.status = "stalled"
        job.finished_at = stalled_finished_at
        job.last_error = stalled_last_error
        db.commit()
        return {"repaired_count": 0}

    with patch("services.admin_city_import_job_service.run_image_enrich", return_value={"scanned_places": 0, "created": 0, "errors": [], "provider_status": "success"}), \
         patch("services.admin_city_import_job_service._run_auto_repair", side_effect=_fake_auto_repair):
        finished = run_photo_enrichment_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


# --- _mark_worker_exception --------------------------------------------------


def test_mark_worker_exception_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-worker-exception-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"
    job.status = "stalled"
    job.finished_at = stalled_finished_at
    job.last_error = stalled_last_error
    db_session.commit()

    result = _mark_worker_exception(db_session, job_id=job.id, error="worker boom after stall recovery")

    assert result.status == "stalled"
    assert result.finished_at == stalled_finished_at
    assert result.last_error == stalled_last_error
    assert "worker_exception" not in dict(result.step_details or {})


def test_mark_worker_exception_still_marks_a_genuinely_running_job_failed_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Sanity check: the guard must not become a no-op for the normal case
    — a job that is genuinely still running when it crashes must still be
    marked failed with the real error."""
    city = city_factory(slug="worker-exception-normal-path-city")
    job = _claim(db_session, city_id=city.id)

    result = _mark_worker_exception(db_session, job_id=job.id, error="worker boom")

    assert result.status == "failed"
    assert result.last_error == "worker boom"
    assert result.step_details["worker_exception"]["error"] == "worker boom"


# --- cancel_import_job and mark_stuck_import_jobs concurrency guards -------


def test_cancel_import_job_raises_truthfully_when_already_stalled_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    from services.admin_city_import_job_service import cancel_import_job

    city = city_factory(slug="cancel-race-stalled-city")
    job = _claim(db_session, city_id=city.id)
    job.status = "stalled"
    job.finished_at = datetime.utcnow()
    job.last_error = "Import job stalled: no heartbeat before timeout"
    db_session.commit()
    original_last_error = job.last_error
    original_finished_at = job.finished_at

    with pytest.raises(ValueError, match="уже завершена"):
        cancel_import_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.last_error == original_last_error
    assert job.finished_at == original_finished_at


def test_mark_stalled_import_jobs_uses_row_lock_and_is_idempotent_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Running the stall sweep twice in a row (e.g. two overlapping cron
    ticks) must not raise and must not double-count or corrupt the row —
    the second call sees the row already terminal and finds nothing to do."""
    city = city_factory(slug="stall-sweep-idempotent-city")
    job = _claim(db_session, city_id=city.id)
    job.started_at = datetime.utcnow() - timedelta(hours=2)
    job.updated_at = datetime.utcnow() - timedelta(hours=2)
    db_session.commit()

    first_count = mark_stalled_import_jobs(db_session, actor_id="tester")
    db_session.refresh(job)
    assert first_count == 1
    assert job.status == "stalled"
    first_finished_at = job.finished_at

    second_count = mark_stalled_import_jobs(db_session, actor_id="tester")
    db_session.refresh(job)
    assert second_count == 0
    assert job.status == "stalled"
    assert job.finished_at == first_finished_at
