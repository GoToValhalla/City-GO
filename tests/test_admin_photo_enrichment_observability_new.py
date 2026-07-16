from __future__ import annotations

from services import admin_city_import_job_service as service
from services.admin_extended_service import get_admin_import_job
from models.city_admin_import_job import CityAdminImportJob


def test_photo_enrichment_success_with_zero_created_is_visible_in_details(db_session, city_factory, place_factory, monkeypatch):
    city = city_factory(slug="photo-observable", name="Photo Observable", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-observable-1", title="Photo Observable 1", image_url=None)
    place_factory(city_id=city.id, slug="photo-observable-2", title="Photo Observable 2", image_url=None)
    result = {
        "city_slug": city.slug,
        "scanned_places": 5,
        "created": 0,
        "candidates_found": 0,
        "provider_status": "source_evidence_exhausted",
        "errors": [{"place_id": 1, "error": "no source evidence"}],
        "warnings": ["No image candidates found from trusted sources, Wikimedia Commons, or Openverse."],
    }
    logs: list[dict[str, object]] = []

    def fake_run_image_enrich(argv: list[str]) -> dict[str, object]:
        assert argv == ["--city", city.slug, "--limit", str(service.IMAGE_LIMIT), "--apply"]
        active_job = db_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).one()
        assert active_job.status == "running"
        assert active_job.source == service.SOURCE_PHOTO_ENRICHMENT
        assert active_job.current_step == "finding_images"
        assert active_job.started_at is not None
        return result

    def fake_log_import_event(db, event: str, city_slug: str, actor_id: str | None, message: str, details: dict[str, object] | None = None, level: str = "info", job_id: int | None = None):
        logs.append({"event": event, "city_slug": city_slug, "actor_id": actor_id, "message": message, "details": details or {}})

    monkeypatch.setattr(service, "run_image_enrich", fake_run_image_enrich)
    monkeypatch.setattr(service, "log_import_event", fake_log_import_event)

    queued = service.queue_city_import_job(db_session, city_id=city.id, actor_id="test-admin")
    db_session.commit()
    claimed = service.claim_queued_job(db_session, job_id=queued.id, worker_id="test-worker", actor_id="test-admin")
    job = service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin", job_id=claimed.id)

    assert job.status == "success_with_warnings"
    assert job.source == service.SOURCE_PHOTO_ENRICHMENT
    assert job.current_step == "snapshot_refresh"
    assert job.finished_at is not None
    assert job.places_found == 5
    assert job.places_saved == 0
    assert job.total_items == 5
    assert job.processed_items == 5
    assert job.failed_items == 1
    assert job.step_details is not None
    assert job.step_details["photo_enrichment"] == {**result, "photo_diagnostics": job.step_details["photo_enrichment"]["photo_diagnostics"]}
    assert job.step_details[service.SNAPSHOT_KEY]["data_coverage"]["places_total"] == 2
    assert job.step_details[service.SNAPSHOT_KEY]["data_coverage"]["without_photo"] == 2

    finished = next(item for item in logs if item["event"] == "photo_enrichment_finished")
    details = finished["details"]
    assert details["job_id"] == job.id
    assert details["source"] == service.SOURCE_PHOTO_ENRICHMENT
    assert details["photo_enrichment"]["created"] == 0
    assert details["photo_enrichment"]["scanned_places"] == 5
    assert details["photo_enrichment"]["candidates_found"] == 0
    assert details["photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
    assert details["photo_diagnostics"]["provider_status"] == "provider_request_error"
    assert details["photo_enrichment"]["errors"] == [{"place_id": 1, "error": "no source evidence"}]

    detail = get_admin_import_job(db_session, city.id)
    assert detail is not None
    assert detail["step_details"]["photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
    assert detail["step_details"]["latest_photo_enrichment"]["provider_status"] == "source_evidence_exhausted"

    queued_snapshot = service.queue_city_snapshot_refresh_job(db_session, city_id=city.id, actor_id="test-admin")
    db_session.commit()
    claimed_snapshot = service.claim_queued_job(db_session, job_id=queued_snapshot.id, worker_id="test-worker", actor_id="test-admin")
    snapshot_job = service.run_snapshot_refresh_job(db_session, city_id=city.id, actor_id="test-admin", job_id=claimed_snapshot.id)
    snapshot_detail = get_admin_import_job(db_session, city.id)
    assert snapshot_job.source == service.SOURCE_SNAPSHOT_REFRESH
    assert snapshot_detail is not None
    assert snapshot_detail["source"] == service.SOURCE_SNAPSHOT_REFRESH
    assert snapshot_detail["step_details"]["latest_photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
    assert snapshot_detail["step_details"]["photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
