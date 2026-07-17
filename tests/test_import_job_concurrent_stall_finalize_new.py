"""Single-session regression coverage for the atomic finalization design
fixed in response to independent review of commit
23deba98003814af2c5d2d6ce0a05ba99b82e65b:

finalize_import_job(db, job_id=..., new_status=..., expected_claimed_by=...,
fields=...) is database-authoritative — it re-selects the exact row under
SELECT ... FOR UPDATE with populate_existing() and verifies status ==
"running", claimed_by == expected_claimed_by (when checked), and
finished_at IS NULL, all under that lock, before writing anything. This
replaces the earlier version that trusted the caller's already-loaded ORM
object, which cannot detect a status change committed by a DIFFERENT
PostgreSQL transaction (expire_on_commit only fires on this Session's own
commits, never on another connection's).

These tests use a single sqlite session with a mutated row to prove the
FUNCTION's own logic is correct (does it read the DB fresh? does it reject
on lost ownership? does it write only inside the fields dict?). They do
NOT reproduce the actual two-connection lost-update race — that requires
two independent Sessions/connections against a database with real
row-level locking, which sqlite cannot provide. See
tests_postgres_integration/test_concurrent_job_finalization.py for the
real two-connection PostgreSQL reproduction of every scenario below.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services import admin_city_import_job_service
from services.admin_city_import_job_service import (
    claim_queued_job,
    queue_city_import_job,
    run_address_enrichment_job,
    run_city_import_job,
    run_enrichment_only_job,
    run_photo_enrichment_job,
    run_snapshot_refresh_job,
    finalize_import_job,
)
from services.admin_city_import_tasks import _mark_worker_exception, mark_stalled_import_jobs


def _claim(db, *, city_id, actor_id="tester", worker_id="worker-1"):
    queued = queue_city_import_job(db, city_id=city_id, actor_id=actor_id)
    db.commit()
    return claim_queued_job(db, job_id=queued.id, worker_id=worker_id, actor_id=actor_id)


# --- finalize_import_job itself ----------------------------------------------------


def testfinalize_import_job_applies_and_writes_fields_atomically_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="try-finalize-valid-city")
    job = _claim(db_session, city_id=city.id)
    finished_at = datetime.utcnow()

    result = finalize_import_job(
        db_session, job_id=job.id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": finished_at, "last_error": None},
    )

    assert result.ok is True
    assert result.job.status == "success"
    assert result.job.finished_at == finished_at


def testfinalize_import_job_rereads_db_fresh_ignoring_stale_caller_object_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """The exact defect from the review: a caller's ALREADY-LOADED `job`
    object still shows status="running" in Python, but the row was
    already updated (simulating a different transaction's commit) —
    finalize_import_job must observe the DB's current value, not the stale
    Python attribute."""
    city = city_factory(slug="try-finalize-fresh-read-city")
    job = _claim(db_session, city_id=city.id)
    # Mutate the row via a raw UPDATE (bypassing the ORM object `job`
    # entirely) to simulate "a different transaction already committed
    # this" without going through the same Session/object.
    db_session.execute(
        CityAdminImportJob.__table__.update()
        .where(CityAdminImportJob.id == job.id)
        .values(status="stalled", finished_at=datetime.utcnow(), last_error="stalled by someone else")
    )
    db_session.commit()
    # `job` (the Python object) may still be stale here depending on
    # SQLAlchemy internals — the point of this test is that finalize_import_job
    # does not rely on it at all; it queries fresh by job_id.
    assert job.id is not None

    result = finalize_import_job(
        db_session, job_id=job.id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )

    assert result.ok is False
    assert result.reason == "already_terminalized"
    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.last_error == "stalled by someone else"


def testfinalize_import_job_rejects_wrong_claimed_by_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A runner presenting the WRONG expected_claimed_by (e.g. a stale
    worker identity from a previous, already-superseded claim) must not
    be able to finalize the row even if status is still "running"."""
    city = city_factory(slug="try-finalize-wrong-owner-city")
    job = _claim(db_session, city_id=city.id, worker_id="worker-real")

    result = finalize_import_job(
        db_session, job_id=job.id, new_status="success", expected_claimed_by="worker-impostor", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )

    assert result.ok is False
    assert result.reason == "lost_ownership"
    db_session.refresh(job)
    assert job.status == "running"


def testfinalize_import_job_no_ownership_check_when_expected_claimed_by_omitted_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Administrative override path: omitting expected_claimed_by entirely
    (the sentinel default) means "finalize regardless of who holds it" —
    used by mark_stalled_import_jobs/cancel_import_job/mark_stuck_import_jobs,
    which have already re-locked the row for their own reasons."""
    city = city_factory(slug="try-finalize-admin-override-city")
    job = _claim(db_session, city_id=city.id, worker_id="worker-real")

    result = finalize_import_job(db_session, job_id=job.id, new_status="stalled", actor_id="admin")

    assert result.ok is True
    assert result.job.status == "stalled"


def testfinalize_import_job_writes_nothing_on_rejection_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A rejected finalize must not leave ANY partial field write — not
    even the fields dict's contents — on the row."""
    city = city_factory(slug="try-finalize-no-partial-write-city")
    job = _claim(db_session, city_id=city.id)
    original_step_details = dict(job.step_details or {})
    db_session.execute(
        CityAdminImportJob.__table__.update()
        .where(CityAdminImportJob.id == job.id)
        .values(status="cancelled", finished_at=datetime.utcnow())
    )
    db_session.commit()

    result = finalize_import_job(
        db_session, job_id=job.id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"step_details": {"should_not_appear": True}, "last_error": "should not appear either"},
    )

    assert result.ok is False
    db_session.refresh(job)
    assert "should_not_appear" not in dict(job.step_details or {})
    assert job.last_error != "should not appear either"


# --- Every runner must not clobber a concurrently-stalled row's fields ------


def test_run_city_import_job_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-full-import-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_pipeline(db, *, job, city, actor_id, force=True, notify_completion=True):
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
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
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
        db.commit()
        raise RuntimeError("provider crashed after stall recovery already ran")

    with patch("services.admin_city_import_job_service.run_enrichment_pipeline", side_effect=_fake_pipeline_raises):
        finished = run_city_import_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    assert finished.status == "stalled"
    assert finished.finished_at == stalled_finished_at
    assert finished.last_error == stalled_last_error


def test_run_snapshot_refresh_job_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """run_snapshot_refresh_job computes its step_details snapshot via the
    pure, non-writing _build_light_snapshot_step_details BEFORE calling
    finalize_import_job, then folds the result into finalize_import_job's
    own atomic fields= write — this simulates a concurrent stall race
    landing in that exact window, between the pure computation and the
    lock-protected finalize call, and proves finalize_import_job's own
    re-verification under lock (not the pre-computed step_details) is what
    decides the outcome."""
    city = city_factory(slug="stall-race-snapshot-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    real_build = admin_city_import_job_service._build_light_snapshot_step_details

    def _fake_build(db, *, city, job, source):
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
        db.commit()
        return real_build(db, city=city, job=job, source=source)

    with patch("services.admin_city_import_job_service._build_light_snapshot_step_details", side_effect=_fake_build):
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
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
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
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
        db.commit()
        raise RuntimeError("provider crashed after stall recovery already ran")

    with patch("services.admin_city_import_job_service.run_enrichment_only_pipeline", side_effect=_fake_enrichment_only_raises):
        with pytest.raises(RuntimeError):
            run_enrichment_only_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    # The original `job` object is no longer session-managed: a rejected
    # finalize_import_job call expunges it (see
    # test_finalize_import_job_expunges_stale_object_on_rejection_new), so
    # a fresh row must be re-queried rather than db.refresh(job).
    reloaded = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
    assert reloaded.status == "stalled"
    assert reloaded.finished_at == stalled_finished_at
    assert reloaded.last_error == stalled_last_error


def test_run_address_enrichment_job_blocked_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """No places in the city => the "blocked" path's own finalize_import_job(...,
    "failed", ...) call must likewise be rejected if the row was already
    stalled by the time it runs. Exercises finalize_import_job directly since
    _resolve_run_job would otherwise refuse to hand back an already-stalled
    row before we even reach the finalize call."""
    city = city_factory(slug="stall-race-address-blocked-city")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"
    db_session.execute(
        CityAdminImportJob.__table__.update()
        .where(CityAdminImportJob.id == job.id)
        .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
    )
    db_session.commit()

    result = finalize_import_job(
        db_session, job_id=job.id, new_status="failed", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow(), "last_error": "should not appear"},
    )

    assert result.ok is False
    # `job` was expunged from db_session by the rejected finalize call —
    # re-query rather than db.refresh(job).
    reloaded = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
    assert reloaded.status == "stalled"
    assert reloaded.finished_at == stalled_finished_at
    assert reloaded.last_error == stalled_last_error


def test_run_photo_enrichment_job_success_path_does_not_clobber_concurrently_stalled_job_new(db_session: Session, city_factory: Callable[..., Any], place_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="stall-race-photo-city")
    place_factory(city_id=city.id, slug="stall-race-photo-place", title="Stall Race Photo Place")
    job = _claim(db_session, city_id=city.id)
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"

    def _fake_auto_repair(db, *, city, job, changed_place_ids):
        db.execute(
            CityAdminImportJob.__table__.update()
            .where(CityAdminImportJob.id == job.id)
            .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
        )
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
    job = _claim(db_session, city_id=city.id, worker_id="worker-1")
    stalled_finished_at = datetime.utcnow() - timedelta(minutes=5)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"
    db_session.execute(
        CityAdminImportJob.__table__.update()
        .where(CityAdminImportJob.id == job.id)
        .values(status="stalled", finished_at=stalled_finished_at, last_error=stalled_last_error)
    )
    db_session.commit()

    result = _mark_worker_exception(db_session, job_id=job.id, error="worker boom after stall recovery", expected_claimed_by="worker-1")

    assert result.status == "stalled"
    assert result.finished_at == stalled_finished_at
    assert result.last_error == stalled_last_error
    assert "worker_exception" not in dict(result.step_details or {})


def test_mark_worker_exception_still_marks_a_genuinely_running_job_failed_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Sanity check: the guard must not become a no-op for the normal case
    — a job that is genuinely still running when it crashes, with the
    correct claimed_by, must still be marked failed with the real error."""
    city = city_factory(slug="worker-exception-normal-path-city")
    job = _claim(db_session, city_id=city.id, worker_id="worker-1")

    result = _mark_worker_exception(db_session, job_id=job.id, error="worker boom", expected_claimed_by="worker-1")

    assert result.status == "failed"
    assert result.last_error == "worker boom"
    assert result.step_details["worker_exception"]["error"] == "worker boom"


def test_mark_worker_exception_rejects_wrong_claimed_by_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A stale/wrong worker identity must not be able to mark a job that
    some OTHER worker is genuinely still running as failed."""
    city = city_factory(slug="worker-exception-wrong-owner-city")
    job = _claim(db_session, city_id=city.id, worker_id="worker-real")

    result = _mark_worker_exception(db_session, job_id=job.id, error="impostor's error", expected_claimed_by="worker-impostor")

    assert result.status == "running"
    assert result.last_error is None


# --- cancel_import_job and mark_stalled_import_jobs concurrency guards -----


def test_cancel_import_job_raises_truthfully_when_already_stalled_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    from services.admin_city_import_job_service import cancel_import_job

    city = city_factory(slug="cancel-race-stalled-city")
    job = _claim(db_session, city_id=city.id)
    original_last_error = "Import job stalled: no heartbeat before timeout"
    original_finished_at = datetime.utcnow()
    db_session.execute(
        CityAdminImportJob.__table__.update()
        .where(CityAdminImportJob.id == job.id)
        .values(status="stalled", finished_at=original_finished_at, last_error=original_last_error)
    )
    db_session.commit()

    with pytest.raises(ValueError, match="уже завершена"):
        cancel_import_job(db_session, city_id=city.id, actor_id="tester", job_id=job.id)

    # `job` was expunged from db_session by the rejected finalize_import_job
    # call inside cancel_import_job — re-query rather than db.refresh(job).
    reloaded = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
    assert reloaded.status == "stalled"
    assert reloaded.last_error == original_last_error
    assert reloaded.finished_at == original_finished_at


def test_cancel_import_job_overrides_ownership_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """An admin cancel is an intentional override — it must succeed even
    though it isn't the claimed_by owner, unlike a runner's own finalize."""
    from services.admin_city_import_job_service import cancel_import_job

    city = city_factory(slug="cancel-overrides-ownership-city")
    job = _claim(db_session, city_id=city.id, worker_id="worker-real")

    cancelled = cancel_import_job(db_session, city_id=city.id, actor_id="admin", job_id=job.id)

    assert cancelled.status == "cancelled"


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
