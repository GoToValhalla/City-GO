from datetime import datetime
from unittest.mock import patch

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.admin_city_import_job_payload import build_import_job_payload
from services.admin_city_import_job_service import queue_city_import_job, run_city_import_job
from services.admin_city_import_runner import summarize_import_results


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
    assert summary["status"] == "failed"


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
    fake_result = {
        "results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 3, "created": 2, "updated": 0}}]
    }
    def _fake_pipeline(db, *, job, city, actor_id, force=True):
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
