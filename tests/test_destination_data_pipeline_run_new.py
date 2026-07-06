from __future__ import annotations

from models.admin_audit_log import AdminAuditLog
from models.destination_data_pipeline import DestinationDataPipelineRun
from tests.destination_pipeline_helpers import destination_with_scope


def test_destination_pipeline_starts_full_run_and_latest_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory)
    response = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "full", "idempotency_key": "run-1"})
    assert response.status_code == 200
    payload = response.json()["run"]
    assert payload["status"] == "succeeded"
    assert payload["counters"]["candidates_found"] == 3
    assert payload["counters"]["places_created"] == 3
    latest = client.get(f"/admin/destinations/{dest.slug}/data-pipeline/latest")
    assert latest.status_code == 200
    assert latest.json()["run"]["id"] == payload["id"]
    assert db_session.query(AdminAuditLog).filter(AdminAuditLog.action == "destination_pipeline_run_finished").count() == 1


def test_destination_pipeline_idempotency_does_not_duplicate_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="idem-dest")
    body = {"mode": "full", "idempotency_key": "same-key"}
    first = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json=body).json()["run"]
    second = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json=body).json()["run"]
    assert first["id"] == second["id"]
    assert db_session.query(DestinationDataPipelineRun).filter_by(destination_id=dest.id).count() == 1


def test_destination_pipeline_history_and_stop_completed_conflict_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="history-dest")
    run = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"}).json()["run"]
    history = client.get(f"/admin/destinations/{dest.slug}/data-pipeline/runs")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    detail = client.get(f"/admin/destinations/{dest.slug}/data-pipeline/runs/{run['id']}")
    assert detail.json()["run"]["id"] == run["id"]
    stop = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/runs/{run['id']}/stop")
    assert stop.status_code == 409
