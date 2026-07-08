"""Repeated admin clicks on "Добрать фото"/"Добрать адреса" (or any queue
action) must not create duplicate active jobs — must return an explicit
409 with job_id/reason instead of silently enqueuing a duplicate or
failing generically."""

from __future__ import annotations

from models.city_admin_import_job import CityAdminImportJob


def _create_active_job(db_session, *, city_id: int, status: str, source: str) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status=status, source=source)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_double_enrich_photo_click_returns_existing_job_reason_no_duplicate_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="dup-photo-city")
    existing = _create_active_job(db_session, city_id=city.id, status="running", source="admin_photo_enrichment")

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-photos")

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["result"] == "blocked"
    assert body["reason"] == "duplicate_active_job"
    assert body["job_id"] == existing.id
    assert body["job_status"] == "running"

    jobs = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).all()
    assert len(jobs) == 1


def test_double_enrich_address_click_returns_existing_job_reason_no_duplicate_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="dup-address-city")
    existing = _create_active_job(db_session, city_id=city.id, status="queued", source="admin_address_enrichment")

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-addresses")

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["result"] == "blocked"
    assert body["reason"] == "duplicate_active_job"
    assert body["job_id"] == existing.id
    assert body["job_status"] == "queued"

    jobs = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).all()
    assert len(jobs) == 1


def test_enrich_photos_after_job_finished_creates_new_queue_entry_new(client, db_session, city_factory) -> None:
    """A finished (non-active) job must not block a fresh queue action."""
    city = city_factory(slug="finished-photo-city")
    _create_active_job(db_session, city_id=city.id, status="success", source="admin_photo_enrichment")

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-photos")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"


def test_stale_failed_job_does_not_block_new_enrichment_new(client, db_session, city_factory) -> None:
    """A stalled/failed job (not queued/running) must not block a new action."""
    city = city_factory(slug="stale-failed-city")
    _create_active_job(db_session, city_id=city.id, status="stalled", source="admin_photo_enrichment")

    response = client.post(f"/admin/import-jobs/{city.id}/enrich-photos")

    assert response.status_code == 200
