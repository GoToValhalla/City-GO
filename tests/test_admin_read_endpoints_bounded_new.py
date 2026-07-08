"""Admin/public read endpoints must stay lightweight, bounded, and observable
while an import/enrichment worker is active — no heavy diagnostics, no
mutation, no unhandled exceptions on DB failure."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from models.city_admin_import_job import CityAdminImportJob


def test_enrich_addresses_action_only_queues_does_not_run_heavy_backfill_new(client: TestClient, db_session, city_factory, monkeypatch) -> None:
    """POST /admin/import-jobs/{city_id}/enrich-addresses must only flip the job
    to queued and commit — the actual backfill must never run synchronously here."""
    city = city_factory(slug="enrich-addresses-queue-only", name="Enrich Addresses Queue Only")
    backfill_calls: list[object] = []
    monkeypatch.setattr("data.scripts.backfill_missing_place_addresses.run", lambda argv: backfill_calls.append(argv))

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-addresses")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    job = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).one()
    assert job.status == "queued"
    assert backfill_calls == []


def test_snapshot_refresh_now_does_not_mutate_publication_state_new(client: TestClient, db_session, city_factory, place_factory) -> None:
    """refresh-now recomputes coverage/change-summary diagnostics only — it
    must never touch is_published/is_active/launch_status."""
    city = city_factory(slug="refresh-now-no-mutation-city", launch_status="published", is_active=True)
    place = place_factory(city_id=city.id, slug="refresh-now-no-mutation-place", title="Refresh Now No Mutation Place", is_published=True)
    db_session.commit()
    before_launch_status = city.launch_status
    before_is_active = city.is_active
    before_place_published = place.is_published

    response = client.post(f"/admin/import-jobs/{city.id}/snapshot/refresh-now")

    assert response.status_code == 200
    db_session.refresh(city)
    db_session.refresh(place)
    assert city.launch_status == before_launch_status
    assert city.is_active == before_is_active
    assert place.is_published == before_place_published


def test_system_logs_with_no_rows_returns_200_empty_list_new(client: TestClient) -> None:
    response = client.get("/admin/system-logs?city_slug=nonexistent-city&module=import&limit=50")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_system_logs_db_failure_returns_structured_503_not_unhandled_exception_new(client: TestClient, monkeypatch) -> None:
    """A DB-level failure (connection drop, statement timeout) must surface as
    a bounded structured JSON error, not an unhandled 500/"Load failed"."""
    def raising_list_system_logs(*args, **kwargs):
        raise SQLAlchemyError("simulated connection failure")

    monkeypatch.setattr("routers.admin_place_ops.list_system_logs", raising_list_system_logs)

    response = client.get("/admin/system-logs?city_slug=kaliningrad&module=import&limit=50")

    assert response.status_code == 503
    body = response.json()
    assert "detail" in body


def test_health_endpoint_does_not_touch_db_or_admin_diagnostics_new(client: TestClient, monkeypatch) -> None:
    """GET /health must be a pure process-liveness check — it must not import
    or call anything DB/admin-diagnostics related."""
    def fail_if_called(*args, **kwargs):
        raise AssertionError("GET /health must not touch the database")

    monkeypatch.setattr("core.readiness.check_database_ready", fail_if_called)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_uses_minimal_bounded_db_check_new(client: TestClient, monkeypatch) -> None:
    """GET /ready must call the minimal SELECT 1 readiness check, not a heavier
    admin/aggregation query, and must report a structured error on DB failure."""
    calls: list[str] = []

    def fake_check_database_ready():
        calls.append("checked")
        return True, "ok"

    monkeypatch.setattr("main.check_database_ready", fake_check_database_ready)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert calls == ["checked"]


def test_ready_endpoint_reports_503_on_db_failure_new(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("main.check_database_ready", lambda: (False, "OperationalError"))

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "OperationalError"


def test_import_queue_summary_does_not_execute_worker_new(client: TestClient, city_factory, monkeypatch) -> None:
    """GET /admin/import-queue is a read-only summary — it must never call
    run_queued_import_jobs or otherwise execute worker iterations."""
    city_factory(slug="queue-summary-read-only", name="Queue Summary Read Only")
    worker_calls: list[object] = []
    monkeypatch.setattr("routers.admin_import_queue.run_queued_import_jobs", lambda **kwargs: worker_calls.append(kwargs))

    response = client.get("/admin/import-queue")

    assert response.status_code == 200
    assert worker_calls == []
