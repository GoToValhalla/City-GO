"""Prerequisite checks and blocked-reason reporting for standalone admin
enrichment actions (Добрать фото / Добрать адреса), so eligible-but-never-run
is never confused with ran-and-found-nothing."""

from __future__ import annotations

from services import admin_city_import_job_service as service
from services.admin_city_import_job_payload import build_import_job_payload


def test_photo_enrichment_with_no_places_exposes_blocked_reason_new(db_session, city_factory) -> None:
    city = city_factory(slug="prereq-photo-no-places-city", launch_status="importing", is_active=False)

    job = service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    assert job.status == "failed"
    assert job.step_details["prerequisites"]["ok"] is False
    assert job.step_details["prerequisites"]["blocked_reason"] == "no_places_in_city"
    assert job.step_details["photo_enrichment"]["scanned_places"] == 0
    assert "заблокирован" in job.last_error


def test_photo_enrichment_blocked_run_is_not_silently_reported_as_success_new(db_session, city_factory) -> None:
    city = city_factory(slug="prereq-photo-not-silent-city", launch_status="importing", is_active=False)

    job = service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    diagnostics = job.step_details["photo_diagnostics"]
    assert diagnostics["provider_status"] != "success"
    assert diagnostics["provider_status"] == "blocked"
    assert diagnostics["provider_warning"]


def test_address_enrichment_with_no_places_exposes_blocked_reason_new(db_session, city_factory) -> None:
    city = city_factory(slug="prereq-address-no-places-city", launch_status="importing", is_active=False)

    job = service.run_address_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    assert job.status == "failed"
    assert job.step_details["prerequisites"]["ok"] is False
    assert job.step_details["prerequisites"]["blocked_reason"] == "no_places_in_city"
    assert job.step_details["address_enrichment"]["scanned_places"] == 0
    assert "заблокирован" in job.last_error


def test_photo_enrichment_creates_real_pending_work_when_prerequisites_met_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="prereq-photo-runs-city", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="prereq-photo-place", title="Prereq Photo Place", image_url=None)
    monkeypatch.setattr(service, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 1, "created": 0, "candidates_found": 0, "provider_status": "source_evidence_exhausted", "errors": []})

    job = service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    assert job.step_details["prerequisites"]["ok"] is True
    assert job.step_details["photo_enrichment"]["scanned_places"] == 1


def test_address_enrichment_creates_real_pending_work_when_prerequisites_met_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="prereq-address-runs-city", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="prereq-address-place", title="Prereq Address Place", address=None)
    monkeypatch.setattr(service, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 1, "updated": 0, "errors": 0})

    job = service.run_address_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    assert job.step_details["prerequisites"]["ok"] is True
    assert job.step_details["address_enrichment"]["checked"] == 1


def test_admin_payload_exposes_enrichment_prerequisites_top_level_new(db_session, city_factory) -> None:
    city = city_factory(slug="prereq-payload-city", launch_status="importing", is_active=False)
    service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    payload = build_import_job_payload(db_session, city)

    assert payload["enrichment_prerequisites"] is not None
    assert payload["enrichment_prerequisites"]["blocked_reason"] == "no_places_in_city"


def test_finding_images_dependency_failed_is_visible_in_admin_payload_new(db_session, city_factory, place_factory) -> None:
    """A schema_mismatch collecting_places failure that skips finding_images
    (dependency_failed) must be visible through photo_diagnostics, not silent."""
    from models.city_admin_import_job import CityAdminImportJob

    city = city_factory(slug="prereq-dependency-failed-city", launch_status="import_failed", is_active=False)
    place_factory(city_id=city.id, slug="prereq-dependency-place", title="Dependency Place", image_url=None)
    job = CityAdminImportJob(
        city_id=city.id,
        status="stalled",
        source="admin_city_import",
        current_step="error",
        step_details={
            "warnings": [
                {"step": "collecting_places", "error": "tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist"},
                {"step": "finding_images", "status": "skipped", "reason": "dependency_failed", "dependency": "collecting_places"},
            ],
        },
    )
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    assert payload["photo_diagnostics"]["provider_status"] == "step_skipped_due_to_dependency_failure"
    assert payload["photo_diagnostics"]["zero_result_reason"] == "dependency_failed"
