from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import routers.admin_import_queue as admin_import_queue_module
from models.city_admin_import_job import CityAdminImportJob


@pytest.fixture(autouse=True)
def _reset_run_once_lock():
    admin_import_queue_module._run_once_in_progress = False
    yield
    admin_import_queue_module._run_once_in_progress = False


def _create_import_job(db_session: Session, *, city_id: int, status: str, source: str = "admin_city_import") -> CityAdminImportJob:
    """Create an admin import job for endpoint-level queue contract tests."""
    job = CityAdminImportJob(city_id=city_id, status=status, source=source)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_enrich_photos_action_only_queues_does_not_run_heavy_scan_in_web_request(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """POST /admin/import-jobs/{city_id}/enrich-photos must only flip the job
    to queued and commit — the actual scan (run_image_enrich) must never be
    called synchronously inside this request."""
    city = city_factory(slug="enrich-photos-queue-only", name="Enrich Photos Queue Only")
    scan_calls: list[Any] = []
    monkeypatch.setattr("data.scripts.enrich_place_images.run", lambda argv: scan_calls.append(argv))

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-photos")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    job = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).one()
    assert job.status == "queued"
    assert scan_calls == []


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


def test_admin_import_queue_run_once_blocked_by_default(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """Default (no override) must NOT execute heavy worker iterations inside
    the web process — queued jobs are processed by import-worker instead."""
    city_factory(slug="queue-run-once-blocked", name="Queue Run Once Blocked")
    calls: list[dict[str, Any]] = []

    def fake_run_queued_import_jobs(*, actor_id: str, limit: int) -> dict[str, Any]:
        calls.append({"actor_id": actor_id, "limit": limit})
        return {"processed": 0, "failed": 0, "stalled": 0, "errors": []}

    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", fake_run_queued_import_jobs)
    monkeypatch.setattr("routers.admin_import_queue.settings.admin_allow_in_web_worker_run_once", False)

    response = client.post("/admin/import-queue/run-once?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled"] is False
    assert payload["result"] == "blocked"
    assert "import-worker" in payload["reason"]
    assert "queue" in payload

    time.sleep(0.1)
    assert calls == []


def test_admin_import_queue_run_once_executes_when_override_enabled(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """With ADMIN_ALLOW_IN_WEB_WORKER_RUN_ONCE enabled, the endpoint still
    dispatches to an isolated daemon thread, not FastAPI's shared threadpool."""
    city = city_factory(slug="queue-run-once", name="Queue Run Once")
    queued_job = _create_import_job(db_session, city_id=city.id, status="queued")
    calls: list[dict[str, Any]] = []

    def fake_run_queued_import_jobs(*, actor_id: str, limit: int) -> dict[str, Any]:
        calls.append({"actor_id": actor_id, "limit": limit})
        return {"processed": 0, "failed": 0, "stalled": 0, "errors": []}

    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", fake_run_queued_import_jobs)
    monkeypatch.setattr("routers.admin_import_queue.settings.admin_allow_in_web_worker_run_once", True)

    response = client.post("/admin/import-queue/run-once?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled"] is True
    assert payload["result"] == "success"
    assert payload["limit"] == 2
    assert payload["queue"]["queued"] == 1
    assert payload["queue"]["running"] == 0
    assert payload["queue"]["next_job_ids"] == [queued_job.id]

    for _ in range(50):
        if calls:
            break
        time.sleep(0.02)
    assert calls == [{"actor_id": "test-admin", "limit": 2}]


def test_admin_import_queue_run_once_does_not_block_the_request_on_slow_worker(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """The endpoint must return immediately even if the worker iteration is slow
    (e.g. photo enrichment blocked on external providers) — it must never run on
    Starlette's shared sync threadpool, which public/admin request handlers
    (like GET /api/cities/available) also depend on."""
    city_factory(slug="queue-run-once-slow", name="Queue Run Once Slow")
    started = threading.Event()

    def slow_run_queued_import_jobs(*, actor_id: str, limit: int) -> dict[str, Any]:
        started.set()
        time.sleep(2)
        return {"processed": 0, "failed": 0, "stalled": 0, "errors": []}

    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", slow_run_queued_import_jobs)
    monkeypatch.setattr("routers.admin_import_queue.settings.admin_allow_in_web_worker_run_once", True)

    request_start = time.monotonic()
    response = client.post("/admin/import-queue/run-once?limit=1")
    request_elapsed = time.monotonic() - request_start

    assert response.status_code == 200
    assert request_elapsed < 1.0, "run-once must return before the slow worker iteration completes"

    for _ in range(50):
        if started.is_set():
            break
        time.sleep(0.02)
    assert started.is_set()


def test_admin_import_queue_run_once_concurrent_call_returns_409(
    client: TestClient,
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch,
) -> None:
    """When override is enabled, only one in-web worker iteration may run at a
    time — a second call while one is in flight must be rejected, not queued
    or silently dropped."""
    city_factory(slug="queue-run-once-concurrent", name="Queue Run Once Concurrent")
    release = threading.Event()
    entered = threading.Event()

    def blocking_run_queued_import_jobs(*, actor_id: str, limit: int) -> dict[str, Any]:
        entered.set()
        release.wait(timeout=5)
        return {"processed": 0, "failed": 0, "stalled": 0, "errors": []}

    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", blocking_run_queued_import_jobs)
    monkeypatch.setattr("routers.admin_import_queue.settings.admin_allow_in_web_worker_run_once", True)

    try:
        first = client.post("/admin/import-queue/run-once?limit=1")
        assert first.status_code == 200
        assert entered.wait(timeout=2)

        second = client.post("/admin/import-queue/run-once?limit=1")
        assert second.status_code == 409
    finally:
        release.set()
        for _ in range(50):
            if not admin_import_queue_module._run_once_in_progress:
                break
            time.sleep(0.02)
