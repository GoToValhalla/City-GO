from models.city_admin_import_job import CityAdminImportJob
from models.place_photo_candidate import PlacePhotoCandidate
from services import admin_city_import_job_service as job_service
from services.admin_city_import_job_payload import build_import_job_payload
from services.import_pipeline_foundation import run_foundation_pipeline


def test_import_pipeline_admin_endpoints_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-api")
    place = place_factory(city_id=city.id, slug="api-place", title="API Place", category="park", address=None)
    place.source = "category_fallback"
    place.confidence = 0.9
    place.image_url = "https://example.test/api.jpg"
    db_session.commit()

    run = client.post(f"/admin/place-enrichment/pipeline/{city.slug}/run")
    assert run.status_code == 200
    payload = run.json()
    assert payload["city_slug"] == city.slug
    assert payload["status"] == "queued"
    assert payload["counters"] == {}

    job = db_session.query(CityAdminImportJob).filter_by(id=payload["job_id"]).one()
    assert job.source == "admin_city_import"

    run_foundation_pipeline(db_session, city=city, job=job, actor="qa")

    steps = client.get(f"/admin/place-enrichment/jobs/{payload['job_id']}/steps")
    assert steps.status_code == 200
    assert {item["step_name"] for item in steps.json()} >= {"collect_places", "enrich_external_sources", "apply_publication_decisions"}

    confidence = client.get(f"/admin/place-enrichment/places/{place.id}/confidence")
    assert confidence.status_code == 200
    assert {item["field_name"] for item in confidence.json()} >= {"title", "address", "photo"}

    review = client.get(f"/admin/place-enrichment/review-queue?city_slug={city.slug}")
    assert review.status_code == 200
    assert review.json()

    resolved = client.post(f"/admin/place-enrichment/review-queue/{review.json()[0]['id']}/resolve", json={"resolution": "fixed"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    candidate = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).one()
    primary = client.post(f"/admin/place-enrichment/photo-candidates/{candidate.id}/set-primary")
    assert primary.status_code == 400


def test_failed_import_does_not_fake_snapshot_created_new(db_session, city_factory, monkeypatch) -> None:
    """Reproduces the Kaliningrad-shaped failure end-to-end through the real
    run_city_import_job entrypoint: all scopes fail with a provider/DNS error
    before any snapshot-worthy progress is made. The admin payload must not
    claim a snapshot exists, and must explain why it does not."""

    city = city_factory(slug="kaliningrad-like-no-snapshot")
    job = CityAdminImportJob(city_id=city.id, status="queued", source=job_service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    def fake_collection_all_scopes_fail(db, *, job, city, actor_id, force, notify_completion=True):
        raise RuntimeError("tourist_core: Failed to resolve overpass-api.de (DNS failure)")

    monkeypatch.setattr(job_service, "run_enrichment_pipeline", fake_collection_all_scopes_fail)

    result = job_service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

    assert result.status == "failed"
    payload = build_import_job_payload(db_session, city)
    # A failed run with zero places produces a snapshot that honestly reflects
    # empty coverage, rather than either faking a healthy snapshot or omitting
    # one silently — the admin-visible warning must say why it's not usable.
    assert payload["snapshot_warning"] is not None
    assert payload["snapshot_warning"]["code"] in {"SNAPSHOT_MISSING", "SNAPSHOT_EMPTY_COVERAGE"}
    assert payload["snapshot_warning"]["repair_required"] is True


def test_admin_import_response_exposes_durable_failure_state_new(db_session, city_factory, monkeypatch) -> None:
    """Admin API response must expose scopes_total/scopes_succeeded/scopes_failed,
    the error message, and a non-success final status for a run where every
    scope failed — it must not show fake success."""

    city = city_factory(slug="kaliningrad-like-durable-failure")
    job = CityAdminImportJob(city_id=city.id, status="queued", source=job_service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    dns_error = "tourist_core: Failed to resolve overpass-api.de (DNS failure)"

    def fake_collection_all_scopes_fail(db, *, job, city, actor_id, force, notify_completion=True):
        job.status = "failed"
        job.last_error = dns_error
        job.scopes_total = 3
        job.scopes_succeeded = 0
        job.places_found = 0
        job.places_saved = 0
        job.step_details = {
            **dict(job.step_details or {}),
            "warnings": [{"step": "collecting_places", "error": dns_error, "kind": "scope_failure"}],
        }
        db.commit()
        return {"import": {"scopes_total": 3, "scopes_succeeded": 0, "last_error": dns_error}}

    monkeypatch.setattr(job_service, "run_enrichment_pipeline", fake_collection_all_scopes_fail)

    result = job_service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")
    assert result.status != "success"

    payload = build_import_job_payload(db_session, city)
    assert payload["job_execution_failed"] is True
    assert payload["last_error"] is not None
    assert dns_error in payload["last_error"]
    summary = payload["import_execution_summary"]
    assert summary["scopes_total"] == 3
    assert summary["scopes_succeeded"] == 0
    assert summary["scopes_failed"] == 3
