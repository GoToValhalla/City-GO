from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import build_import_job_payload


def test_reviewable_import_with_saved_places_syncs_progress_counts_new(db_session) -> None:
    city = City(name="Review Count City", slug="review-count-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(
        city_id=city.id,
        status="partial_success",
        current_step="ready_for_review",
        total_items=0,
        processed_items=0,
        successful_items=0,
        places_found=0,
        places_saved=0,
    )
    place = Place(city_id=city.id, slug="review-count-place", title="Review Count Place", lat=55.0, lng=37.0, category="park")
    db_session.add_all([job, place])
    db_session.commit()

    payload = build_import_job_payload(db_session, city)
    db_session.refresh(job)

    assert payload["status"] == "partial_success"
    assert payload["launch_status"] == "review_required"
    assert payload["places_total"] == 1
    assert payload["total_items"] == 1
    assert payload["processed_items"] == 1
    assert job.step_details["reviewable_count_sync"]["places_total"] == 1


def test_reviewable_import_without_places_returns_to_failed_new(db_session) -> None:
    city = City(name="Empty Review City", slug="empty-review-city", country="Россия", launch_status="review_required", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(
        city_id=city.id,
        status="partial_success",
        current_step="ready_for_review",
        total_items=0,
        processed_items=0,
        successful_items=0,
        places_found=0,
        places_saved=0,
    )
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)
    db_session.refresh(job)
    db_session.refresh(city)

    assert payload["status"] == "failed"
    assert payload["launch_status"] == "import_failed"
    assert payload["places_total"] == 0
    assert payload["can_publish"] is False
    assert payload["can_retry"] is True
    assert city.launch_status == "import_failed"
    assert job.current_step == "error"
    assert job.step_details["empty_review_recovery"]["reason"] == "reviewable_import_without_saved_places"
