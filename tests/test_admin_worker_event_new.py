"""Tests for POST /admin/system-logs/worker-event — the structured worker
lifecycle event ingress used by .github/workflows/run-import-worker-safe.yml.
Reuses write_system_log; no new logging system."""

from __future__ import annotations

from typing import Any, Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic
from services.system_log_service import list_system_logs


def _create_job(db: Session, *, city_id: int, **kwargs: Any) -> CityAdminImportJob:
    defaults: dict[str, Any] = dict(city_id=city_id, status="queued", source="admin_city_import", current_step="created")
    defaults.update(kwargs)
    job = CityAdminImportJob(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_worker_run_started_without_job_id_is_not_associated_with_any_job(client: TestClient, db_session: Session) -> None:
    """A pre-claim lifecycle event (no job claimed yet) must never invent a
    job association — it must be stored without request_id."""
    response = client.post(
        "/admin/system-logs/worker-event",
        json={"event": "worker_run_started", "worker_run_id": "run-1"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    rows, total = list_system_logs(db_session, module="import_worker")
    assert total >= 1
    matching = [row for row in rows if (row.details or {}).get("event") == "worker_run_started"]
    assert matching
    assert matching[0].request_id is None


def test_worker_event_with_job_id_is_associated_with_that_job(client: TestClient, db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="worker-event-scoped")
    job = _create_job(db_session, city_id=city.id, status="running")

    response = client.post(
        "/admin/system-logs/worker-event",
        json={
            "event": "worker_health_check_failed",
            "job_id": job.id,
            "stop_reason": "health_check_failed_health=000_ready=200_streak=1",
        },
    )

    assert response.status_code == 200
    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)
    assert diagnostic is not None
    assert diagnostic["stop_reason"] == "health_check_failed_health=000_ready=200_streak=1"


def test_unknown_event_is_rejected(client: TestClient) -> None:
    response = client.post("/admin/system-logs/worker-event", json={"event": "not_a_real_event"})

    assert response.status_code == 422


def test_workflow_run_url_and_run_id_are_persisted_and_returned(client: TestClient, db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="worker-event-workflow-url")
    job = _create_job(db_session, city_id=city.id, status="running")

    response = client.post(
        "/admin/system-logs/worker-event",
        json={
            "event": "worker_run_started",
            "job_id": job.id,
            "worker_run_id": "29192806410",
            "workflow_name": "CITY GO · OPS · Run Import Worker Safely",
            "github_run_id": "29192806410",
            "github_run_url": "https://github.com/GoToValhalla/City-GO/actions/runs/29192806410",
        },
    )

    assert response.status_code == 200
    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)
    assert diagnostic is not None
    assert diagnostic["workflow_run_id"] == "29192806410"
    assert diagnostic["workflow_run_url"] == "https://github.com/GoToValhalla/City-GO/actions/runs/29192806410"
    assert "actions/runs/29192806410" in diagnostic["diagnostic_report"]
