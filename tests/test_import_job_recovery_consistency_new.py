"""Recovery consistency: admin-recovered import jobs must not be resurrected by
a worker that is still mid-run, and queue/job-card state must agree afterward."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import build_import_job_payload
from services.admin_city_import_tasks import mark_stalled_import_jobs
from services.admin_import_display import job_execution_failed, resolve_import_display
from services.import_pipeline import runner as import_runner


def _stuck_job(db_session, city, *, hours_ago: float = 4) -> CityAdminImportJob:
    started = datetime.utcnow() - timedelta(hours=hours_ago)
    job = CityAdminImportJob(
        city_id=city.id,
        status="running",
        source="admin_city_import",
        current_step="collecting_places",
        started_at=started,
        updated_at=started,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_stuck_running_job_recovery_leaves_queue_and_job_card_agreeing_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="recovery-consistency-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=4)

    queue_before = client.get("/admin/import-queue").json()
    assert queue_before["running"] == 1
    assert queue_before["stalled_running"] == 1

    response = client.post("/admin/import-queue/mark-stalled")
    assert response.status_code == 200
    assert response.json()["marked"] == 1

    queue_after = client.get("/admin/import-queue").json()
    assert queue_after["running"] == 0
    assert queue_after["stalled_running"] == 0

    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "stalled"
    assert job.current_step == "error"

    payload = build_import_job_payload(db_session, city)
    assert payload["status"] == "stalled"
    assert payload["status_group"] == "failed"
    assert payload["job_execution_failed"] is True
    assert payload["status"] != "running"
    assert payload["current_step_label"] != "Выполняется"


def test_second_recovery_call_is_idempotent_and_does_not_corrupt_state_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="recovery-idempotent-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=4)

    first = client.post("/admin/import-queue/mark-stalled")
    assert first.json()["marked"] == 1

    second = client.post("/admin/import-queue/mark-stalled")
    assert second.status_code == 200
    assert second.json()["marked"] == 0
    assert second.json()["job_ids"] == []

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.current_step == "error"

    queue = client.get("/admin/import-queue").json()
    assert queue["running"] == 0
    assert queue["stalled_running"] == 0


def test_admin_queue_and_job_endpoint_agree_after_recovery_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="recovery-agreement-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=4)
    client.post("/admin/import-queue/mark-stalled")

    queue = client.get("/admin/import-queue").json()
    assert queue["running"] == 0
    assert queue["stalled_running"] == 0
    assert job.id not in queue["running_job_ids"]
    assert job.id not in queue["stale_job_ids"]

    jobs_response = client.get("/admin/import-jobs?limit=50")
    assert jobs_response.status_code == 200
    row = next(item for item in jobs_response.json()["items"] if item["city_id"] == city.id)
    assert row["status"] == "stalled"
    assert row["status_group"] == "failed"
    assert row["job_execution_failed"] is True


def test_worker_cannot_complete_an_already_recovered_job_new(db_session, city_factory, monkeypatch) -> None:
    """Simulates the real race: the pipeline is still executing collecting_places
    when an admin marks the job stalled; the worker's own finalize step must not
    resurrect it back to running/success afterward."""
    city = city_factory(slug="recovery-race-city", launch_status="importing", is_active=False)
    place = Place(city_id=city.id, slug="recovery-race-place", title="Recovery Race Place", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()

    def fake_run_osm_import_only(*_args, **_kwargs):
        # Simulate an admin recovering the job while collecting_places is running.
        mark_stalled_import_jobs(db_session, actor_id="test-admin", now=datetime.utcnow() + timedelta(minutes=31))
        return {"results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 1, "created": 0, "updated": 0}}]}

    monkeypatch.setattr(import_runner, "run_osm_import_only", fake_run_osm_import_only)
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 0, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 1.0})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)

    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "stalled"
    assert job.status != "success"
    assert job.status != "running"
    assert job_execution_failed(job) is True

    display = resolve_import_display(city, job)
    assert display["status_group"] == "failed"
