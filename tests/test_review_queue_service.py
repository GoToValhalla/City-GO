from __future__ import annotations

from models.city_admin_import_job import CityAdminImportJob
from services.review_queue_service import ensure_review_item


def test_review_queue_drops_invalid_job_id_without_breaking_import(db_session, city_factory, place_factory):
    city = city_factory(slug="review-invalid-job", name="Review Invalid Job")
    place = place_factory(city_id=city.id, slug="review-invalid-job-place", title="Review Invalid Job Place")

    item = ensure_review_item(
        db_session,
        city_id=city.id,
        place_id=place.id,
        field_name="photo",
        reason="missing_photo",
        job_id=999999,
        payload={"source": "collector"},
    )
    db_session.commit()
    db_session.refresh(item)

    assert item.job_id is None
    assert item.payload == {"source": "collector", "dropped_invalid_job_id": 999999}


def test_review_queue_keeps_valid_city_admin_import_job_id(db_session, city_factory, place_factory):
    city = city_factory(slug="review-valid-job", name="Review Valid Job")
    place = place_factory(city_id=city.id, slug="review-valid-job-place", title="Review Valid Job Place")
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", current_step="collecting_places")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    item = ensure_review_item(
        db_session,
        city_id=city.id,
        place_id=place.id,
        field_name="address",
        reason="missing_address",
        job_id=job.id,
    )
    db_session.commit()
    db_session.refresh(item)

    assert item.job_id == job.id
    assert item.payload == {}
