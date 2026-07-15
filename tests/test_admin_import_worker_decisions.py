from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.system_log import SystemLog
from services import admin_city_import_tasks as tasks


class _SessionContext:
    """Reuse the pytest DB session without closing it from service-level SessionLocal calls."""

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def __enter__(self) -> Session:
        return self.db_session

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _patch_session_local(monkeypatch, db_session: Session) -> None:
    monkeypatch.setattr(tasks, "SessionLocal", lambda: _SessionContext(db_session))


def _create_import_job(db_session: Session, *, city_id: int, status: str = "queued", source: str = "admin_city_import") -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status=status, source=source)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _events(db_session: Session) -> list[str]:
    logs = db_session.query(SystemLog).filter(SystemLog.module == "import_worker").order_by(SystemLog.id.asc()).all()
    return [str((row.details or {}).get("event")) for row in logs]


def test_import_worker_logs_no_queued_jobs(
    db_session: Session,
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["queue"]["queued"] == 0
    assert _events(db_session) == ["worker_no_queued_jobs"]


def test_import_worker_blocks_full_import_in_safe_mode_on_low_memory_host(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 0)
    city = city_factory(slug="worker-safe-mode-block", name="Worker Safe Mode Block")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("run_city_import_job must not be called when safe mode blocks the job")

    monkeypatch.setattr(tasks, "run_city_import_job", fail_if_called)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    db_session.refresh(job)
    assert job.status == "queued"
    assert job.last_error is None
    assert job.finished_at is None
    assert _events(db_session) == ["worker_job_blocked_safe_mode"]


def test_import_worker_blocks_heavy_job_when_memory_reading_is_unknown(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: None)
    city = city_factory(slug="worker-memory-unknown", name="Worker Memory Unknown")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    monkeypatch.setattr(
        tasks,
        "run_city_import_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("heavy job must fail closed")),
    )

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    db_session.refresh(job)
    assert job.status == "queued"
    assert job.last_error is None


def test_import_worker_blocked_job_stays_queued_and_is_picked_up_once_memory_recovers(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """Regression: a job blocked by the low-memory resource guard must not be
    marked failed or dropped from the queue. It must remain queued, and the
    very next worker run must automatically pick up the same job once host
    memory is reported as sufficient — no manual re-enqueue."""
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    monkeypatch.setattr(tasks.settings, "import_worker_min_job_claim_memory_mb", 550)
    city = city_factory(slug="worker-low-memory-then-recovered", name="Worker Low Memory Then Recovered")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: 532)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("run_city_import_job must not be called while memory is below threshold")

    monkeypatch.setattr(tasks, "run_city_import_job", fail_if_called)

    blocked_result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert blocked_result["processed"] == 0
    assert blocked_result["failed"] == 0
    db_session.refresh(job)
    assert job.status == "queued"
    assert job.last_error is None
    assert job.finished_at is None

    def fake_run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: 711)
    monkeypatch.setattr(tasks, "run_city_import_job", fake_run_city_import_job)

    recovered_result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert recovered_result["processed"] == 1
    db_session.refresh(job)
    assert job.status == "success"


def test_import_worker_allows_heavy_job_when_enabled_and_host_memory_is_sufficient(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    monkeypatch.setattr(tasks.settings, "import_worker_min_job_claim_memory_mb", 550)
    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: 711)
    city = city_factory(slug="worker-heavy-allowed", name="Worker Heavy Allowed")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    def fake_run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "run_city_import_job", fake_run_city_import_job)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 1
    db_session.refresh(job)
    assert job.status == "success"
    assert _events(db_session) == ["worker_job_claimed", "worker_job_finished"]


def test_healthy_post_start_memory_does_not_self_deadlock_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """Regression for the production no-progress defect: preflight passed
    at 603 MB before the worker container started; once running, the
    container's own baseline overhead dropped host MemAvailable to
    520-531 MB. The job-claim gate (import_worker_min_job_claim_memory_mb,
    default 350, separate from the 550 MB startup floor) must NOT reuse the
    startup floor here — a healthy post-start host must not skip the
    queued job forever."""
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    # Default import_worker_min_job_claim_memory_mb (350) is intentionally
    # left untouched here to prove the *default* does not self-deadlock.
    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: 528)
    city = city_factory(slug="worker-post-start-healthy", name="Worker Post Start Healthy")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    def fake_run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "run_city_import_job", fake_run_city_import_job)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 1
    assert result["claimed_jobs"] == [{"job_id": job.id, "terminal_status": "success"}]
    db_session.refresh(job)
    assert job.status == "success"


def test_genuinely_unsafe_post_start_memory_still_blocks_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """The separate, lower job-claim floor must still block a genuinely
    unsafe host — lowering the threshold from the old 550 MB startup value
    must not mean "never block anything"."""
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    monkeypatch.setattr(tasks, "_available_memory_mb", lambda: 200)
    city = city_factory(slug="worker-post-start-unsafe", name="Worker Post Start Unsafe")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("run_city_import_job must not be called under the job-claim memory floor")

    monkeypatch.setattr(tasks, "run_city_import_job", fail_if_called)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    assert result["claimed_jobs"] == []
    db_session.refresh(job)
    assert job.status == "queued"


def test_import_worker_allows_light_jobs_in_safe_mode(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 0)
    city = city_factory(slug="worker-safe-mode-allow", name="Worker Safe Mode Allow")
    job = _create_import_job(db_session, city_id=city.id, source="admin_address_enrichment")

    def fake_run_address_enrichment_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "run_address_enrichment_job", fake_run_address_enrichment_job)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 1
    db_session.refresh(job)
    assert job.status == "success"


def test_import_worker_safe_mode_off_allows_full_import(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", False)
    city = city_factory(slug="worker-safe-mode-off", name="Worker Safe Mode Off")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    def fake_run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "run_city_import_job", fake_run_city_import_job)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 1
    db_session.refresh(job)
    assert job.status == "success"


def test_import_worker_logs_claim_and_finish_for_queued_job(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-claim", name="Worker Claim")
    job = _create_import_job(db_session, city_id=city.id)

    def fake_run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
        queued_job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).one()
        queued_job.status = "success"
        queued_job.started_at = queued_job.started_at or datetime.utcnow()
        queued_job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(queued_job)
        return queued_job

    monkeypatch.setattr(tasks, "run_city_import_job", fake_run_city_import_job)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["queue"]["queued"] == 0
    assert _events(db_session) == ["worker_job_claimed", "worker_job_finished"]
    logs = db_session.query(SystemLog).filter(SystemLog.module == "import_worker").order_by(SystemLog.id.asc()).all()
    assert logs[0].city_slug == "worker-claim"
    assert logs[0].request_id == str(job.id)
    assert logs[0].actor_id == "test-worker"
    assert logs[0].details["job_id"] == job.id
    assert logs[0].details["queued_seconds"] is not None


def test_generic_runtime_exception_marks_job_failed_with_one_event_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """A plain Python exception from job logic (no DB-level failure) must
    still leave the job durably failed with exactly one worker_job_failed
    event, and must not roll back anything committed before this job started
    (e.g. the city row created in this same session just above)."""
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-generic-exception", name="Worker Generic Exception")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_enrichment")

    monkeypatch.setattr(
        tasks,
        "run_enrichment_only_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("worker boom")),
    )
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["errors"] == [{"job_id": job.id, "city_id": city.id, "source": "admin_city_enrichment", "error": "worker boom"}]

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.current_step == "error"
    assert job.last_error == "worker boom"
    assert job.failed_items >= 1
    assert job.finished_at is not None
    assert job.updated_at is not None
    assert job.step_details["worker_exception"]["error"] == "worker boom"

    # The city row committed before run_queued_import_jobs was even called
    # must survive — proving the exception path does not destroy the
    # caller's own already-committed transaction state.
    survived_city = db_session.query(City).filter_by(id=city.id).one()
    assert survived_city.slug == "worker-generic-exception"

    events = _events(db_session)
    assert events == ["worker_job_claimed", "worker_job_failed"]
    failed_log = db_session.query(SystemLog).filter(SystemLog.module == "import_worker", SystemLog.level == "error").one()
    assert failed_log.details["event"] == "worker_job_failed"
    assert failed_log.details["job_id"] == job.id
    assert failed_log.details["city_id"] == city.id
    assert failed_log.details["source"] == "admin_city_enrichment"
    assert failed_log.details["error"] == "worker boom"


def test_system_exit_from_job_runner_marks_job_failed_and_does_not_propagate_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """Regression for a real worker crash found during the E2E rehearsal:
    run_city_import_job's call chain reaches run_due_import_jobs._targets(),
    which raises SystemExit("No configured import targets match filters")
    when a city's launch_status has left importing/imported/review_required
    (e.g. after publication) and a rerun is attempted. SystemExit subclasses
    BaseException, not Exception, so a bare `except Exception` here would let
    it propagate straight out of run_queued_import_jobs and kill the entire
    worker process instead of just failing this one job. Assert the job ends
    up failed with the real message and that run_queued_import_jobs itself
    returns normally (proving the worker loop would survive to poll again)."""
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-system-exit", name="Worker System Exit")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_import")

    monkeypatch.setattr(
        tasks,
        "run_city_import_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(SystemExit("No configured import targets match filters")),
    )
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["errors"] == [
        {"job_id": job.id, "city_id": city.id, "source": "admin_city_import", "error": "No configured import targets match filters"}
    ]

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.current_step == "error"
    assert job.last_error == "No configured import targets match filters"

    events = _events(db_session)
    assert events == ["worker_job_claimed", "worker_job_failed"]

    # The worker loop must survive: a subsequent call must run normally,
    # proving this SystemExit did not tear down anything shared (session,
    # module state) needed for the next poll cycle.
    next_result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)
    assert next_result["processed"] == 0
    assert next_result["failed"] == 0


def test_sqlalchemy_error_recovers_and_marks_job_failed_once_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """A real SQLAlchemy failure (not just a generic exception) must still be
    recovered — the session must remain usable afterward, the job must end
    up failed, and only one worker_job_failed event must be written (no
    duplicate from a retry or from the recovery path itself)."""
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-sqlalchemy-error", name="Worker SQLAlchemy Error")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_enrichment")

    def _raise_integrity_error(*args, **kwargs):
        raise IntegrityError("INSERT INTO x", {}, Exception("duplicate key"))

    monkeypatch.setattr(tasks, "run_enrichment_only_job", _raise_integrity_error)
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["failed"] == 1

    # The session must still be usable after recovering from the aborted
    # transaction — a bare query must succeed with no lingering error state.
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.current_step == "error"
    assert "duplicate key" in job.last_error

    events = _events(db_session)
    assert events.count("worker_job_failed") == 1
    assert events == ["worker_job_claimed", "worker_job_failed"]


def test_failed_job_does_not_leak_system_log_into_next_worker_call_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """A failed job's worker_job_failed log must be scoped to that job only
    — a second, unrelated run_queued_import_jobs call (e.g. a later poll
    with nothing queued) must not see it mixed into its own event list."""
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-no-leak", name="Worker No Leak")
    job = _create_import_job(db_session, city_id=city.id, source="admin_city_enrichment")

    monkeypatch.setattr(
        tasks,
        "run_enrichment_only_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("worker boom")),
    )
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    first_result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)
    assert first_result["failed"] == 1
    assert _events(db_session) == ["worker_job_claimed", "worker_job_failed"]

    second_result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert second_result["failed"] == 0
    assert second_result["processed"] == 0
    assert second_result["queue"]["queued"] == 0
    # Only one NEW event (no_queued_jobs) must be appended — the earlier
    # worker_job_failed from the first call is real history, not a leak,
    # but it must not be duplicated or repeated by the second call.
    events = _events(db_session)
    assert events == ["worker_job_claimed", "worker_job_failed", "worker_no_queued_jobs"]
    assert events.count("worker_job_failed") == 1


def test_failed_job_is_not_left_queued_or_running_in_queue_summary_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    city = city_factory(slug="worker-queue-summary-after-fail", name="Worker Queue Summary After Fail")
    _create_import_job(db_session, city_id=city.id, source="admin_city_enrichment")

    monkeypatch.setattr(
        tasks,
        "run_enrichment_only_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("worker boom")),
    )
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1)

    assert result["queue"]["queued"] == 0
    assert result["queue"]["running"] == 0
    assert result["queue"]["active_total"] == 0


def test_city_slug_never_claims_an_unrelated_queued_city_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks, "run_city_import_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    target_city = city_factory(slug="target-city-slug", name="Target City")
    other_city = city_factory(slug="other-city-slug", name="Other City")
    other_job = _create_import_job(db_session, city_id=other_city.id)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1, city_slug=target_city.slug)

    assert result["processed"] == 0
    assert result["failed"] == 0
    db_session.refresh(other_job)
    assert other_job.status == "queued"


def test_city_slug_claims_only_the_matching_citys_job_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks, "run_city_import_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    target_city = city_factory(slug="claim-target-city", name="Claim Target City")
    other_city = city_factory(slug="claim-other-city", name="Claim Other City")
    target_job = _create_import_job(db_session, city_id=target_city.id)
    other_job = _create_import_job(db_session, city_id=other_city.id)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1, city_slug=target_city.slug)

    assert result["processed"] == 1
    db_session.refresh(other_job)
    assert other_job.status == "queued"
    assert _events(db_session) == ["worker_job_claimed", "worker_job_finished"]
    claimed_log = db_session.query(SystemLog).filter(SystemLog.module == "import_worker").first()
    assert (claimed_log.details or {}).get("job_id") == target_job.id


def test_dry_run_never_claims_or_mutates_the_job_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    called = []
    monkeypatch.setattr(tasks, "run_city_import_job", lambda *args, **kwargs: called.append(1))
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    city = city_factory(slug="dry-run-city", name="Dry Run City")
    job = _create_import_job(db_session, city_id=city.id)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1, dry_run=True)

    assert result["dry_run"] is True
    assert result["would_process"] == [{"job_id": job.id, "city_id": city.id, "source": job.source}]
    assert called == []
    db_session.refresh(job)
    assert job.status == "queued"
    assert _events(db_session) == []


def test_dry_run_reports_no_matching_job_for_unrelated_city_slug_new(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks, "send_admin_alert", lambda **_kwargs: {"sent": True})

    target_city = city_factory(slug="dry-run-target", name="Dry Run Target")
    other_city = city_factory(slug="dry-run-other", name="Dry Run Other")
    _create_import_job(db_session, city_id=other_city.id)

    result = tasks.run_queued_import_jobs(actor_id="test-worker", limit=1, city_slug=target_city.slug, dry_run=True)

    assert result["would_process"] == []
