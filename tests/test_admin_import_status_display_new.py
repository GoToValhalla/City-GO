from __future__ import annotations

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_payload import build_import_job_payload
from services.admin_extended_service import get_admin_import_jobs


def _published_city_with_failed_job(db_session):
    city = City(name="Зеленоградск", slug="zelenogradsk", country="Россия", launch_status="published", is_active=True)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(
        city_id=city.id,
        status="stalled",
        current_step="collecting_places",
        source="admin_city_import",
        total_items=466,
        processed_items=466,
        successful_items=0,
        places_found=0,
        places_saved=0,
        scopes_total=3,
        scopes_succeeded=0,
        failed_items=0,
        last_error="tourist_core: psycopg.errors.UndefinedTable",
        step_details={
            "stalled": True,
            "import_diff": {
                "status": "failed",
                "scopes_total": 3,
                "scopes_succeeded": 0,
                "places_found": 0,
                "places_saved": 0,
            },
            "warnings": [{"step": "collecting_places", "error": "tourist_core: psycopg.errors.UndefinedTable"}],
        },
    )
    db_session.add(job)
    db_session.commit()
    return city, job


def test_published_city_failed_import_shows_failed_status_new(db_session) -> None:
    city, job = _published_city_with_failed_job(db_session)
    payload = build_import_job_payload(db_session, city)
    assert payload["destination_publication_status"] == "published"
    assert payload["job_execution_status"] == "stalled"
    assert payload["status"] == "stalled"
    assert payload["current_step_label"] != "Опубликован"
    assert payload["status_group"] == "failed"
    assert payload["job_execution_failed"] is True
    assert payload["failed_items"] >= 1
    assert payload["import_error_summary"]["failed_step"] == "collecting_places"
    assert "psycopg" in payload["import_error_summary"]["error_message"]
    assert payload["last_error"] is not None
    assert payload["snapshot_warning"]["code"] == "SNAPSHOT_MISSING"


def test_published_city_failed_import_list_payload_new(db_session) -> None:
    city, _job = _published_city_with_failed_job(db_session)
    items, _total = get_admin_import_jobs(db_session)
    row = next(item for item in items if item["city_slug"] == city.slug)
    assert row["status"] == "stalled"
    assert row["destination_publication_status"] == "published"
    assert row["status_group"] == "failed"
    assert row["job_execution_failed"] is True


def test_successful_import_keeps_success_status_new(db_session) -> None:
    city = City(name="OK City", slug="ok-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(
        city_id=city.id,
        status="success",
        current_step="ready_for_review",
        step_details={"import_diff": {"status": "success", "scopes_total": 2, "scopes_succeeded": 2, "places_found": 10, "places_saved": 8}},
    )
    db_session.add(job)
    db_session.commit()
    payload = build_import_job_payload(db_session, city)
    assert payload["status"] == "success"
    assert payload["job_execution_failed"] is False
    assert payload["failed_items"] == 0


def test_discovery_bulk_create_does_not_create_import_job_new(client, monkeypatch, db_session) -> None:
    from models.city_admin_import_job import CityAdminImportJob

    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    before = db_session.query(CityAdminImportJob).count()
    discover = client.post("/admin/discovery/regions/test:RU-KGD/discover", json={"provider": "deterministic"})
    job_id = discover.json()["job"]["id"]
    candidate_id = next(c["id"] for c in discover.json()["preview"]["candidates"] if c["name"] == "Янтарный")
    response = client.post(
        f"/admin/discovery/jobs/{job_id}/bulk-create",
        json={"candidate_ids": [candidate_id], "options": {"queue_import": False}},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1
    assert db_session.query(CityAdminImportJob).count() == before
