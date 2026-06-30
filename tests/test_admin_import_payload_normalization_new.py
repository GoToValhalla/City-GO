from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import build_import_job_payload, refresh_import_job_snapshot
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
