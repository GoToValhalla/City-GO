from __future__ import annotations

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_payload import build_import_job_payload
from services.photo_enrichment_diagnostics import build_photo_enrichment_diagnostics
from services.photo_enrichment_diagnostics.eligibility import filtered_out_by_reason


def test_without_photo_and_no_run_reports_warning_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="photo-diag-no-run", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-1", title="Museum", image_url=None, category="museum")
    diagnostics = build_photo_enrichment_diagnostics(db_session, city)
    assert diagnostics["without_photo_total"] == 1
    assert diagnostics["provider_status"] == "no_photo_enrichment_run"
    assert diagnostics["admin_hint"]
    assert diagnostics["zero_result_reason"] == "photo_enrichment_not_run"


def test_without_photo_and_zero_provider_results_reports_no_candidates_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="photo-diag-zero", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-zero-1", title="Park", image_url=None, category="park")
    result = {
        "scanned_places": 1,
        "created": 0,
        "candidates_found": 0,
        "skipped_no_source": 1,
        "provider_status": "source_evidence_exhausted",
        "places_without_public_image_total": 1,
    }
    diagnostics = build_photo_enrichment_diagnostics(db_session, city, enrichment_result=result, scan_limit=2000)
    assert diagnostics["provider_status"] == "no_candidates_from_provider"
    assert diagnostics["zero_result_reason"] == "no_candidates_from_provider"
    assert diagnostics["filtered_out_by_reason"]["no_source_evidence"] == 1
    assert diagnostics["admin_hint"]


def test_all_places_filtered_out_visible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="photo-diag-filtered", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-filtered-1", title="ATM", image_url=None, category="atm")
    result = {
        "scanned_places": 1,
        "created": 0,
        "candidates_found": 0,
        "skipped_ineligible": 1,
        "provider_status": "source_evidence_exhausted",
        "places_without_public_image_total": 1,
    }
    diagnostics = build_photo_enrichment_diagnostics(db_session, city, enrichment_result=result, scan_limit=2000)
    assert diagnostics["provider_status"] == "all_places_filtered_out"
    assert diagnostics["filtered_out_by_reason"]["service_category"] == 1


def test_dependency_skip_reports_structured_reason_new(db_session, city_factory) -> None:
    city = city_factory(slug="photo-diag-skip")
    diagnostics = build_photo_enrichment_diagnostics(
        db_session,
        city,
        step_status="skipped",
        dependency_step="collecting_places",
    )
    assert diagnostics["provider_status"] == "step_skipped_due_to_dependency_failure"
    assert diagnostics["zero_result_reason"] == "dependency_failed"
    assert diagnostics["admin_hint"]


def test_zero_pending_without_reason_is_forbidden_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="photo-diag-must-explain", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-must-explain-1", title="Tower", image_url=None, category="attraction")
    diagnostics = build_photo_enrichment_diagnostics(db_session, city)
    assert diagnostics["without_photo_total"] > 0
    assert diagnostics["pending_photos_created"] == 0
    assert diagnostics["pending_photos_existing"] == 0
    assert diagnostics["zero_result_reason"]
    assert diagnostics["admin_hint"]


def test_admin_import_display_includes_photo_diagnostics_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="photo-diag-admin", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-admin-1", title="Fort", image_url=None, category="fortress")
    job = CityAdminImportJob(
        city_id=city.id,
        status="success_with_warnings",
        source="admin_photo_enrichment",
        current_step="snapshot_refresh",
        step_details={
            "photo_enrichment": {
                "scanned_places": 1,
                "created": 0,
                "candidates_found": 0,
                "skipped_no_source": 1,
                "provider_status": "source_evidence_exhausted",
            }
        },
    )
    db_session.add(job)
    db_session.commit()
    payload = build_import_job_payload(db_session, city)
    diagnostics = payload["photo_diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["provider_status"] == "no_candidates_from_provider"
    assert payload["step_details"]["photo_diagnostics"]["admin_hint"]
    assert payload["photo_diagnostics"]["without_photo_total"] == 1


def test_filtered_out_by_reason_counts_all_reasons_new(db_session, city_factory, place_factory) -> None:
    """Regression: this scans every without-photo place on every admin import job details
    request (timeout risk for large cities), so it must select only the scalar columns it
    reads instead of hydrating full ORM rows. Verifies counts still match after that change."""
    city = city_factory(slug="photo-diag-perf", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="photo-diag-perf-1", title="ATM", image_url=None, category="atm")
    place_factory(city_id=city.id, slug="photo-diag-perf-2", title="yes", image_url=None, category="museum")

    counts = filtered_out_by_reason(db_session, city_id=city.id)

    assert counts["service_category"] == 1
    assert counts["low_quality_title"] == 1
