from __future__ import annotations

import pytest

from data.scripts.import_city_osm import _enqueue_place_change_review
from models.city_admin_import_job import CityAdminImportJob
from models.import_batch import ImportBatch
from models.review_queue_item import ReviewQueueItem
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.admin_city_import_runner import summarize_import_results
from services.import_pipeline import runner as import_runner
from services.place_import_lifecycle_service import PlaceImportDecision


def test_invalid_import_job_id_does_not_fk_review_queue_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="fk-safe-city")
    place = place_factory(city_id=city.id, slug="fk-safe-place", title="Place", category="park")
    batch = ImportBatch(city_id=city.id, mode="apply", dry_run=False)
    db_session.add(batch)
    db_session.flush()
    decision = PlaceImportDecision(
        action="needs_review",
        status="needs_review",
        is_active=True,
        changed_fields=["title"],
        review_reasons=["source_data_changed"],
        change_set={"title": {"before": "A", "after": "B"}},
    )

    _enqueue_place_change_review(
        db_session,
        city=city,
        batch=batch,
        city_admin_import_job_id=batch.id,
        place=place,
        decision=decision,
        item={"source_url": "https://www.openstreetmap.org/node/1"},
        before_public={"status": "published"},
    )
    db_session.commit()

    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id).one()
    assert item.job_id is None
    assert item.payload["job_link_issue"]["requested_job_id"] == batch.id


def test_dns_scope_failure_is_classified_without_db_integrity_mix_new() -> None:
    payload = {
        "results": [
            {"scope": "tourist_core", "status": "failed", "error": "tourist_core: <urlopen error [Errno -3] Temporary failure in name resolution>"},
            {"scope": "food_area", "status": "failed", "error": "food_area: psycopg.errors.ForeignKeyViolation review_queue_items_job_id_fkey"},
        ]
    }
    summary = summarize_import_results(payload)

    assert summary["scopes_succeeded"] == 0
    assert summary["scope_errors"][0]["kind"] == "source_failure"
    assert summary["scope_errors"][1]["kind"] == "data_integrity"
    assert "ForeignKeyViolation" in str(summary["last_error"])


def test_all_scopes_failed_marks_job_partial_success_with_diagnostics_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="scope-fail-city", launch_status="published", is_active=True)
    place_factory(city_id=city.id, slug="existing-place", title="Existing", category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    payload = {
        "results": [
            {"scope": "tourist_core", "status": "failed", "error": "tourist_core: Temporary failure in name resolution"},
            {"scope": "food_area", "status": "failed", "error": "food_area: ForeignKeyViolation review_queue_items_job_id_fkey"},
        ]
    }
    summary = summarize_import_results(payload)
    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 0, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.5})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr("services.admin_city_import_job_payload.refresh_import_job_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    db_session.refresh(job)

    assert summary["status"] == "failed"
    assert summary["scope_errors"][0]["kind"] == "source_failure"
    assert summary["scope_errors"][1]["kind"] == "data_integrity"
    assert job.status == "partial_success"
    assert job.finished_at is not None
    assert "ForeignKeyViolation" in (job.last_error or "")
    assert result["import"]["scopes_succeeded"] == 0


def test_failed_import_snapshot_refresh_from_current_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="snapshot-fail-city")
    place_factory(city_id=city.id, slug="snap-place", title="Snap", category="park", address=None)
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="collecting_places failed")
    db_session.add(job)
    db_session.commit()

    snapshot = refresh_import_job_snapshot(db_session, city_id=city.id, source="failed_import_recovery")
    db_session.refresh(job)

    assert snapshot["data_coverage"]["places_total"] >= 1
    assert job.step_details["admin_import_snapshot"]["source"] == "failed_import_recovery"
