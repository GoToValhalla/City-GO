from __future__ import annotations

from fastapi.testclient import TestClient

from models.data_foundation import EnrichmentTask
from tests.test_admin_backlog_breakdown_new import _make_place


def test_backlog_reduction_report_shows_last_run_and_task_stats_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "report-photo-task", image_url=None)

    response = client.post(
        "/admin/overview/backlog-reduction/apply",
        json={"action_code": "enqueue_photo_discovery", "confirmation_text": "APPLY", "limit": 1, "include_samples": True},
    )
    assert response.status_code == 200, response.text
    applied = response.json()
    assert applied["queued_count"] == 1
    assert db_session.query(EnrichmentTask).filter(EnrichmentTask.place_id == place.id).count() == 1

    report_response = client.get("/admin/overview/backlog-reduction/report")

    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert report["last_result"]["job_id"] == applied["job_id"]
    assert report["last_result"]["action_code"] == "enqueue_photo_discovery"
    assert report["summary"]["runs_24h"] >= 1
    assert report["summary"]["queued_24h"] >= 1
    assert report["summary"]["tasks_created_24h"] >= 1
    assert report["summary"]["active_tasks"] >= 1
    photo = next(row for row in report["task_stats"] if row["task_type"] == "photo_discovery")
    assert photo["total_count"] >= 1
    assert photo["active_count"] >= 1
    assert photo["statuses"]["queued"] >= 1
    assert report["recent_runs"][0]["job_id"] == applied["job_id"]


def test_backlog_reduction_report_empty_state_new(client: TestClient) -> None:
    response = client.get("/admin/overview/backlog-reduction/report")

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["last_result"] is None
    assert report["summary"]["runs_24h"] == 0
    assert {row["task_type"] for row in report["task_stats"]} >= {
        "photo_discovery",
        "address_recovery",
        "description_enrichment",
        "verification_recheck",
    }
