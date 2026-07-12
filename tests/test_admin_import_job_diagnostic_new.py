"""Tests for the single-job import diagnostic endpoint/service (mobile-first
diagnostic view). Covers failed/success/cancelled jobs, missing optional
fields, timeline ordering, and job-scope isolation from unrelated logs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic
from services.system_log_service import write_system_log


def _create_job(db: Session, *, city_id: int, **kwargs: Any) -> CityAdminImportJob:
    defaults: dict[str, Any] = dict(
        city_id=city_id,
        status="queued",
        source="admin_city_import",
        current_step="created",
    )
    defaults.update(kwargs)
    job = CityAdminImportJob(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_missing_job_returns_none_new(db_session: Session) -> None:
    assert build_import_job_diagnostic(db_session, job_id=999999) is None


def test_failed_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-failed")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="failed",
        current_step="error",
        last_error="import-worker safety guard: available host memory (532 MB) is below the configured minimum (550 MB)",
        started_at=datetime.utcnow() - timedelta(seconds=30),
        finished_at=datetime.utcnow(),
    )
    write_system_log(
        db_session, level="info", module="import_worker", message=f"Import worker claiming job #{job.id}",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="error", module="import_worker", message=f"Import worker failed job #{job.id}: boom",
        details={"event": "worker_job_failed", "job_id": job.id, "error": "boom"}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "failed"
    assert diagnostic["failure_reason"] is not None and "532 MB" in diagnostic["failure_reason"]
    assert diagnostic["last_completed_step"] == "error"
    assert diagnostic["duration_seconds"] is not None and diagnostic["duration_seconds"] >= 0
    assert len(diagnostic["timeline"]) == 2
    assert diagnostic["timeline"][0]["type"] == "job_claimed"
    assert diagnostic["timeline"][1]["type"] == "failed"
    assert diagnostic["timeline"][1]["severity"] == "error"
    assert "boom" in diagnostic["diagnostic_report"]
    assert "532 MB" in diagnostic["diagnostic_report"]


def test_successful_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-success")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="success",
        current_step="ready_for_review",
        started_at=datetime.utcnow() - timedelta(minutes=2),
        finished_at=datetime.utcnow(),
        places_found=10,
        places_saved=10,
    )
    write_system_log(
        db_session, level="info", module="city_import", message=f"Импорт #{job.id}: success, мест в городе 10",
        details={"event": "import_job_finished", "job_id": job.id, "places_total": 10}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "success"
    assert diagnostic["failure_reason"] is None
    assert diagnostic["last_completed_step"] == "ready_for_review"
    assert len(diagnostic["timeline"]) == 1
    assert diagnostic["timeline"][0]["type"] == "success"
    assert "success" in diagnostic["diagnostic_report"]


def test_cancelled_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-cancelled")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="cancelled",
        current_step="cancelled",
        cancelled_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    write_system_log(
        db_session, level="info", module="city_import", message=f"Импорт #{job.id} отменён без изменения публикации города",
        details={"event": "import_job_cancelled", "job_id": job.id}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "cancelled"
    assert diagnostic["timeline"][0]["type"] == "cancelled"
    assert diagnostic["timeline"][0]["severity"] == "warning"


def test_missing_optional_fields_do_not_break_endpoint_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A freshly-created queued job has no started_at/finished_at/last_error
    and no timeline events yet — the endpoint must still return a complete,
    valid diagnostic with nullable fields as null, not raise."""
    city = city_factory(slug="diag-queued")
    job = _create_job(db_session, city_id=city.id)

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["started_at"] is None
    assert diagnostic["finished_at"] is None
    assert diagnostic["duration_seconds"] is None
    assert diagnostic["failure_reason"] is None
    assert diagnostic["last_completed_step"] is None
    assert diagnostic["worker_state"] is None
    assert diagnostic["worker_run_id"] is None
    assert diagnostic["stop_reason"] is None
    assert diagnostic["exit_code"] is None
    assert diagnostic["oom_killed"] is None
    assert diagnostic["workflow_run_url"] is None
    assert diagnostic["timeline"] == []
    assert diagnostic["diagnostic_report"]


def test_timeline_ordering_is_chronological_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-order")
    job = _create_job(db_session, city_id=city.id, status="running", current_step="collecting_places")
    write_system_log(
        db_session, level="info", module="import_worker", message="first",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="warning", module="import_worker", message="second",
        details={"event": "worker_job_blocked_safe_mode", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="city_import", message="third",
        details={"event": "unified_import_pipeline_finished", "job_id": job.id}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    timestamps = [event["timestamp"] for event in diagnostic["timeline"]]
    assert timestamps == sorted(timestamps)
    assert [event["summary"] for event in diagnostic["timeline"]] == ["first", "second", "third"]


def test_events_from_another_job_are_excluded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-scope")
    job_a = _create_job(db_session, city_id=city.id, status="running")
    job_b = _create_job(db_session, city_id=city.id, status="running")

    write_system_log(
        db_session, level="info", module="import_worker", message=f"claim {job_a.id}",
        details={"event": "worker_job_claimed", "job_id": job_a.id}, request_id=str(job_a.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="import_worker", message=f"claim {job_b.id}",
        details={"event": "worker_job_claimed", "job_id": job_b.id}, request_id=str(job_b.id), commit=True,
    )

    diagnostic_a = build_import_job_diagnostic(db_session, job_id=job_a.id)

    assert diagnostic_a is not None
    assert len(diagnostic_a["timeline"]) == 1
    assert str(job_a.id) in diagnostic_a["timeline"][0]["summary"] or diagnostic_a["timeline"][0]["payload"]["job_id"] == job_a.id


def test_events_from_unrelated_modules_are_excluded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A frontend/health-check/unrelated system log sharing the same
    request_id string coincidentally must not leak into the job timeline —
    only import_worker/city_import modules are included."""
    city = city_factory(slug="diag-unrelated-module")
    job = _create_job(db_session, city_id=city.id, status="running")

    write_system_log(
        db_session, level="info", module="import_worker", message="claimed",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="error", module="frontend", message="unrelated frontend error",
        details={"event": "frontend_error"}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert len(diagnostic["timeline"]) == 1
    assert diagnostic["timeline"][0]["type"] == "job_claimed"


def test_diagnostic_report_is_plain_text_not_raw_json_dump_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-report-text")
    job = _create_job(
        db_session, city_id=city.id, status="failed", current_step="error",
        last_error="boom", started_at=datetime.utcnow(), finished_at=datetime.utcnow(),
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    report = diagnostic["diagnostic_report"]
    assert isinstance(report, str)
    assert not report.strip().startswith("{")
    assert "Job #" in report
    assert city.name in report


def test_api_returns_diagnostic_for_existing_job_new(client, db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-api")
    job = _create_job(db_session, city_id=city.id, status="running", current_step="collecting_places")

    response = client.get(f"/admin/import-jobs/{job.id}/diagnostic")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job.id
    assert body["city_slug"] == "diag-api"
    assert body["status"] == "running"
    assert body["timeline"] == []
    assert body["diagnostic_report"]


def test_api_returns_404_for_missing_job_new(client) -> None:
    response = client.get("/admin/import-jobs/999999/diagnostic")

    assert response.status_code == 404
