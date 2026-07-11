from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

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
    assert job.status == "failed"
    assert job.last_error is not None
    assert "safety guard" in job.last_error
    assert job.finished_at is not None
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
    assert job.status == "failed"
    assert "unknown" in str(job.last_error)


def test_import_worker_allows_heavy_job_when_enabled_and_host_memory_is_sufficient(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    _patch_session_local(monkeypatch, db_session)
    monkeypatch.setattr(tasks.settings, "import_worker_safe_mode", True)
    monkeypatch.setattr(tasks.settings, "import_worker_max_full_import_places_low_memory", 1)
    monkeypatch.setattr(tasks.settings, "import_worker_min_available_memory_mb", 650)
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
