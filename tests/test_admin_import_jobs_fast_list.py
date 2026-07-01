from __future__ import annotations

from datetime import datetime, timedelta

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_payload import SNAPSHOT_KEY
from services.admin_import_jobs_fast import list_admin_import_jobs_fast


def test_fast_import_jobs_list_uses_latest_job_without_historical_snapshot_scan(db_session, city_factory, place_factory, monkeypatch):
    city = city_factory(slug="fast-import-list", name="Fast Import List", launch_status="importing", is_active=False)
    place_factory(city_id=city.id, slug="fast-import-list-place", title="Fast Import List Place", is_published=False)
    old_snapshot_job = CityAdminImportJob(
        city_id=city.id,
        status="success",
        source="admin_city_import",
        current_step="ready_for_review",
        created_at=datetime.utcnow() - timedelta(days=2),
        updated_at=datetime.utcnow() - timedelta(days=2),
        step_details={SNAPSHOT_KEY: {"data_coverage": {"places_total": 99, "places_published": 99}, "change_summary": {}}},
    )
    latest_queued_job = CityAdminImportJob(
        city_id=city.id,
        status="queued",
        source="admin_city_enrichment",
        current_step="queued",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        step_details={},
    )
    db_session.add_all([old_snapshot_job, latest_queued_job])
    db_session.commit()

    from services import admin_extended_service

    monkeypatch.setattr(
        admin_extended_service,
        "_latest_import_snapshots",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fast list must not scan historical snapshots")),
    )

    payload = list_admin_import_jobs_fast(db_session, limit=50, offset=0)

    row = next(item for item in payload["items"] if item["city_id"] == city.id)
    assert row["status"] == "queued"
    assert row["source"] == "admin_city_enrichment"
    assert row["places_total"] == 1
    assert row["auto_refresh_seconds"] == 7
    assert row["can_cancel"] is True
