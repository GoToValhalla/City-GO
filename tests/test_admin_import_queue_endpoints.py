from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob


def _create_import_job(db_session: Session, *, city_id: int, status: str, source: str = "admin_city_import") -> CityAdminImportJob:
    """Create an admin import job for endpoint-level queue contract tests."""
    job = CityAdminImportJob(city_id=city_id, status=status, source=source)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_admin_import_queue_get_returns_read_only_summary(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
) -> None:
    """GET /admin/import-queue returns queue counters without requiring a worker trigger."""
    city = city_factory(slug="queue-read-only", name="Queue Read Only")
    queued_job = _create_import_job(db_session, city_id=city.id, status="queued")
    running_job = _create_import_job(db_session, city_id=city.id, status="running", source="admin_photo_enrichment")

    response = client.get("/admin/import-queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["active_total"] == 2
    assert payload["queued"] == 1
    assert payload["running"] == 1
    assert payload["stalled_running"] == 0
    assert payload["running_job_ids"] == [running_job.id]
    assert payload["next_job_ids"] == [queued_job.id]
    assert payload["by_status"] == {"queued": 1, "running": 1}
    assert payload["by_source"] == {"admin_city_import": 1, "admin_photo_enrichment": 1}
    assert "worker_kicked" not in payload
    assert "scheduled" not in payload


def test_admin_import_queue_run_once_schedules_worker_and_returns_queue(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """POST /admin/import-queue/run-once is the explicit worker trigger and returns queue state."""
    city = city_factory(slug="queue-run-once", name="Queue Run Once")
    queued_job = _create_import_job(db_session, city_id=city.id, status="queued")
    calls: list[dict[str, Any]] = []

    def fake_run_queued_import_jobs(*, actor_id: str, limit: int) -> dict[str, Any]:
        calls.append({"actor_id": actor_id, "limit": limit})
        return {"processed": 0, "failed": 0, "stalled": 0, "errors": []}

    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", fake_run_queued_import_jobs)

    response = client.post("/admin/import-queue/run-once?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled"] is True
    assert payload["limit"] == 2
    assert payload["queue"]["queued"] == 1
    assert payload["queue"]["running"] == 0
    assert payload["queue"]["next_job_ids"] == [queued_job.id]
    assert calls == [{"actor_id": "test-admin", "limit": 2}]
