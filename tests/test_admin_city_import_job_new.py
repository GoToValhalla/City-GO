from datetime import datetime, timedelta
from unittest.mock import patch

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.admin_city_import_job_payload import build_import_job_payload
from services.admin_city_import_job_service import queue_city_import_job, run_city_import_job
from services.admin_city_import_runner import summarize_import_results
from services.admin_city_import_tasks import mark_stalled_import_jobs
from services.admin_extended_service import get_admin_cities


def test_summarize_import_results_new() -> None:
    payload = {
        "results": [
            {"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 10, "created": 4, "updated": 1}},
            {"status": "failed", "scope": "food_area", "error": "timeout"},
        ]
    }
    summary = summarize_import_results(payload)
    assert summary["scopes_total"] == 2
    assert summary["scopes_succeeded"] == 1
    assert summary["places_found"] == 10
    assert summary["places_saved"] == 5
    assert summary["status"] == "partial_success"


def test_summarize_import_results_uses_bbox_fallback_result_new() -> None:
    payload = {"results": [{"status": "success", "scope": "tourist_core", "import_result": {
        "raw_count": 1, "created": 0, "updated": 0,
        "fallback_result": {"import_result": {"raw_count": 8, "created": 3, "updated": 1}},
    }}]}
    summary = summarize_import_results(payload)
    assert summary["places_found"] == 8
    assert summary["places_saved"] == 4
    assert summary["status"] == "success"


def test_queue_and_run_import_job_new(db_session, monkeypatch) -> None:
    city = City(name="Алматы", slug="almaty-job", country="Казахстан", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    db_session.add(CityImportScope(
        city_id=city.id, code="tourist_core", name="Tourist", bbox={"south": 1, "west": 2, "north": 3, "east": 4},
        enabled=True, status="enabled", import_profile="tourist_core", next_run_at=datetime.utcnow(),
    ))
    db_session.commit()
    job = queue_city_import_job(db_session, city_id=city.id)
    assert job.status == "queued"
    fake_result = {"results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 3, "created": 2, "updated": 0}}]}

    def _fake_pipeline(db, *, job, city, actor_id, force=True, notify_completion=True):
        assert notify_completion is False
        job.status = "success"
        job.places_found = 3
        job.places_saved = 2
        job.scopes_succeeded = 1
        db.commit()
        return {"import": fake_result}

    with patch("services.admin_city_import_job_service.run_enrichment_pipeline", side_effect=_fake_pipeline):
        finished = run_city_import_job(db_session, city_id=city.id, actor_id="tester")
    assert finished.status == "success"
    payload = build_import_job_payload(db_session, city)
    assert payload["can_retry"] is True
    assert payload["places_found"] == 3


def test_import_job_run_endpoint_new(client, db_session) -> None:
    city = City(name="Run City", slug="run-city", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.commit()
    db_session.add(CityImportScope(
        city_id=city.id, code="tourist_core-run", name="Tourist", bbox={"south": 1, "west": 2, "north": 3, "east": 4},
        enabled=True, status="enabled", import_profile="tourist_core",
    ))
    db_session.commit()
    response = client.post(f"/admin/import-jobs/{city.id}/run")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_stalled_running_job_is_marked_failed_and_retryable_new(db_session) -> None:
    city = City(name="Stalled City", slug="stalled-city", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="running", current_step="finding_images",
        started_at=datetime.utcnow() - timedelta(hours=2), updated_at=datetime.utcnow() - timedelta(hours=2))
    db_session.add(job)
    db_session.commit()
    count = mark_stalled_import_jobs(db_session, now=datetime.utcnow())
    payload = build_import_job_payload(db_session, city)
    assert count == 1
    assert job.status == "stalled"
    assert city.launch_status == "import_failed"
    assert payload["can_retry"] is True
    assert payload["last_error"]


def test_admin_city_read_does_not_mark_stalled_imports_new(db_session, monkeypatch) -> None:
    city = City(name="Read Stalled City", slug="read-stalled-city", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="running", current_step="collecting_places",
        started_at=datetime.utcnow() - timedelta(hours=2), updated_at=datetime.utcnow() - timedelta(hours=2))
    db_session.add(job)
    db_session.commit()
    alerts = []
    monkeypatch.setattr("services.admin_city_import_tasks.send_admin_alert", lambda **kwargs: alerts.append(kwargs) or {"sent": True})
    items, _total = get_admin_cities(db_session)
    payload = next(item for item in items if item["slug"] == "read-stalled-city")
    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "running"
    assert city.launch_status == "importing"
    assert payload["launch_status"] == "importing"
    assert alerts == []


def test_failed_import_with_saved_places_moves_to_manual_review_new(db_session) -> None:
    from models.place import Place
    city = City(name="Saved Failed City", slug="saved-failed-city", country="Россия", launch_status="import_failed", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="failed", current_step="error", last_error="photo provider timeout")
    place = Place(city_id=city.id, slug="saved-place", title="Saved Place", lat=55.0, lng=37.0, category="park")
    db_session.add_all([job, place])
    db_session.commit()
    payload = build_import_job_payload(db_session, city)
    db_session.refresh(job)
    db_session.refresh(city)
    assert city.launch_status == "review_required"
    assert job.status == "partial_success"
    assert job.current_step == "ready_for_review"
    assert job.last_error == "photo provider timeout"
    assert job.step_details["failed_import_recovery"]["places_total"] == 1
    assert payload["can_publish"] is True
    assert payload["can_retry"] is True


def test_non_blocking_photo_failure_keeps_city_review_required_new(db_session, monkeypatch) -> None:
    from models.place import Place
    from services.import_pipeline.runner import run_enrichment_pipeline
    city = City(name="Partial City", slug="partial-city", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([job, Place(city_id=city.id, slug="partial-park", title="Partial Park", lat=55.0, lng=37.0, category="park")])
    db_session.commit()
    monkeypatch.setattr("services.import_pipeline.runner.run_osm_import_only", lambda *_args, **_kwargs: {"results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 1, "created": 0, "updated": 0}}]})
    monkeypatch.setattr("services.import_pipeline.runner.run_address_backfill", lambda *_args, **_kwargs: {"checked": 1, "updated": 0, "errors": 0})
    monkeypatch.setattr("services.import_pipeline.runner.run_image_enrich", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("photo api down")))
    monkeypatch.setattr("services.import_pipeline.runner.run_quality_cleanup", lambda *_args, **_kwargs: {"updated": 1})
    monkeypatch.setattr("services.import_pipeline.runner.compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 10})
    run_enrichment_pipeline(db_session, job=job, city=city, actor_id="test-admin")
    assert job.status == "success_with_warnings"
    assert city.launch_status == "review_required"
    assert job.step_details["warnings"][0]["step"] == "finding_images"
