from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import build_import_job_payload, refresh_import_job_snapshot
from services.admin_extended_service import get_admin_import_jobs
from services.admin_extended_service import get_admin_cities


def test_import_detail_uses_snapshot_new(db_session) -> None:
    city = City(name="Snapshot City", slug="snapshot-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="partial_success", current_step="ready_for_review")
    place = Place(city_id=city.id, slug="snapshot-place", title="Snapshot Place", lat=55.0, lng=37.0, category="park")
    db_session.add_all([job, place])
    db_session.commit()
    refresh_import_job_snapshot(db_session, city_id=city.id, source="test")
    payload = build_import_job_payload(db_session, city)
    assert payload["places_total"] == 1
    assert payload["data_coverage"]["places_total"] == 1
    assert payload["step_details"]["snapshot_stale"] is False


def test_snapshot_refresh_does_not_scan_import_job_changes_new(db_session, monkeypatch) -> None:
    city = City(name="No Changes Snapshot", slug="no-changes-snapshot", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="success", current_step="ready_for_review")
    place = Place(city_id=city.id, slug="coverage-place", title="Coverage Place", lat=55.0, lng=37.0, category="park", address=None, image_url=None, short_description=None)
    db_session.add_all([job, place])
    db_session.commit()
    monkeypatch.setattr("services.admin_import_job_change_service.import_job_changes_summary", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("must not scan changes")))

    snapshot = refresh_import_job_snapshot(db_session, city_id=city.id, source="test")

    assert snapshot["data_coverage"]["places_total"] == 1
    assert snapshot["data_coverage"]["without_address"] == 1
    assert snapshot["data_coverage"]["without_photo"] == 1
    assert snapshot["data_coverage"]["without_description"] == 1
    assert snapshot["change_summary"]["created"] == 0
    assert snapshot["change_summary"]["total_changes"] == 0


def test_import_detail_without_snapshot_is_read_only_new(db_session) -> None:
    city = City(name="Read Only City", slug="read-only-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="partial_success", current_step="ready_for_review")
    db_session.add(job)
    db_session.commit()
    payload = build_import_job_payload(db_session, city)
    db_session.refresh(job)
    db_session.refresh(city)
    assert payload["status"] == "partial_success"
    assert city.launch_status == "review_required"
    assert job.status == "partial_success"
    assert payload["step_details"]["snapshot_stale"] is True


def test_completed_success_with_queued_step_is_retryable_not_active_new(db_session) -> None:
    city = City(name="Completed Retry City", slug="completed-retry-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="success", current_step="queued")
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    assert payload["status_group"] != "queued"
    assert payload["can_retry"] is True
    assert payload["can_run"] is False
    assert payload["can_cancel"] is False


def test_published_city_with_active_job_shows_active_state_new(db_session) -> None:
    city = City(name="Published Active City", slug="published-active-city", country="Россия", launch_status="published", is_active=True)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="running", current_step="snapshot_refresh", source="admin_snapshot_refresh")
    db_session.add(job)
    db_session.commit()

    detail = build_import_job_payload(db_session, city)
    items, _total = get_admin_import_jobs(db_session)
    row = next(item for item in items if item["city_slug"] == city.slug)

    assert detail["status"] == "running"
    assert detail["current_step"] == "snapshot_refresh"
    assert detail["can_publish"] is False
    assert row["status"] == "running"
    assert row["status_group"] == "running"
    assert row["can_cancel"] is True


def test_admin_city_list_is_read_only_new(db_session) -> None:
    city = City(name="List Read Only", slug="list-read-only", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="partial_success", current_step="ready_for_review")
    db_session.add(job)
    db_session.commit()
    items, _total = get_admin_cities(db_session)
    payload = next(item for item in items if item["slug"] == "list-read-only")
    db_session.refresh(city)
    db_session.refresh(job)
    assert payload["launch_status"] == "review_required"
    assert city.launch_status == "review_required"
    assert job.status == "partial_success"
