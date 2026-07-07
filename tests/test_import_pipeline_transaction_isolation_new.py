from __future__ import annotations

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.import_pipeline import runner as import_runner
from services.import_pipeline.steps import STEP_COLLECTING_PLACES, STEP_FINDING_IMAGES
from services.import_pipeline.transaction import (
    is_aborted_transaction_error,
    record_step_isolation,
    rollback_session,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def test_collecting_places_failure_records_rollback_before_next_step_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="tx-rollback-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="tx-place", title="Tx Place", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    recovery_calls: list[str] = []
    query_calls = {"count": 0}
    original_query = db_session.query

    def _fake_recover(db: Session, job: CityAdminImportJob, *, step: str, error: BaseException | None = None) -> dict[str, object]:
        recovery_calls.append(step)
        return {
            "step": "transaction_isolation",
            "status": "rolled_back",
            "after_step": step,
            "reason": "db_error_recovered",
        }

    def _query_with_poison(*args, **kwargs):
        model = args[0] if args else None
        if model is Place and query_calls["count"] == 0:
            query_calls["count"] += 1
            raise SQLAlchemyError("InFailedSqlTransaction: current transaction is aborted")
        return original_query(*args, **kwargs)

    summary = {
        "scopes_total": 3,
        "scopes_succeeded": 0,
        "places_found": 0,
        "places_saved": 0,
        "status": "failed",
        "last_error": "tourist_core: source unavailable",
        "scope_errors": [{"scope": "tourist_core", "error": "source unavailable", "kind": "source_failure"}],
    }
    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(import_runner, "summarize_import_results", lambda _payload: summary)
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 1, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.5})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "recover_after_db_error", _fake_recover)
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(db_session, "query", _query_with_poison)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    job = db_session.get(CityAdminImportJob, job.id)

    assert recovery_calls == [STEP_COLLECTING_PLACES]
    isolation = next(item for item in job.step_details["warnings"] if item.get("reason") == "db_error_recovered")
    assert isolation["after_step"] == STEP_COLLECTING_PLACES
    assert result["import"]["last_error"] == "tourist_core: source unavailable"
    assert any(
        item.get("step") == STEP_COLLECTING_PLACES and "source unavailable" in str(item.get("error", ""))
        for item in job.step_details["warnings"]
    )


def test_finding_images_runs_after_collecting_places_failure_without_aborted_transaction_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="tx-images-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="tx-images-place", title="Tx Images", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    image_calls: list[str] = []

    monkeypatch.setattr(
        import_runner,
        "run_osm_import_only",
        lambda *_args, **_kwargs: {"results": [{"status": "failed", "scope": "tourist_core", "error": "dns"}]},
    )
    monkeypatch.setattr(
        import_runner,
        "summarize_import_results",
        lambda _payload: {
            "scopes_total": 1,
            "scopes_succeeded": 0,
            "places_found": 0,
            "places_saved": 0,
            "status": "failed",
            "last_error": "tourist_core: dns",
            "scope_errors": [],
        },
    )
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 1, "updated": 0, "errors": 0})
    monkeypatch.setattr(
        import_runner,
        "run_image_enrich",
        lambda *_args, **_kwargs: image_calls.append("images") or {"scanned_places": 1, "created": 0, "failed": 0},
    )
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.4})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)

    assert image_calls == ["images"]
    assert result["images"]["scanned_places"] == 1
    assert not is_aborted_transaction_error(Exception(str(result["images"].get("error") or "")))


def test_original_collecting_places_error_stays_in_summary_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="tx-summary-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="tx-summary-place", title="Tx Summary", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    original_error = "food_area: locked_elsewhere"

    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(
        import_runner,
        "summarize_import_results",
        lambda _payload: {
            "scopes_total": 2,
            "scopes_succeeded": 0,
            "status": "failed",
            "last_error": original_error,
            "places_found": 0,
            "places_saved": 0,
            "scope_errors": [],
        },
    )
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 0, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    job = db_session.get(CityAdminImportJob, job.id)

    assert result["import"]["last_error"] == original_error
    assert any(original_error in str(item.get("error")) for item in job.step_details["warnings"] if item.get("step") == STEP_COLLECTING_PLACES)


def test_optional_step_skip_reports_dependency_failed_new(db_session, city_factory) -> None:
    city = city_factory(slug="tx-skip-city")
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import")
    db_session.add(job)
    db_session.commit()
    warnings: list[dict[str, object]] = []

    skipped = import_runner._optional_step(
        db_session,
        job,
        city.slug,
        "qa",
        STEP_FINDING_IMAGES,
        warnings,
        lambda: {"scanned_places": 0},
        skip_if_dependency_failed=True,
        dependency_step=STEP_COLLECTING_PLACES,
    )

    assert skipped["status"] == "skipped"
    assert skipped["reason"] == "dependency_failed"
    assert skipped["dependency"] == STEP_COLLECTING_PLACES
    assert warnings[0] == skipped


def test_snapshot_refresh_works_after_rollback_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="tx-snapshot-city")
    place_factory(city_id=city.id, slug="tx-snapshot-place", title="Snap", category="park")
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="collecting_places failed")
    db_session.add(job)
    db_session.commit()

    record_step_isolation(
        db_session,
        job,
        after_step=STEP_COLLECTING_PLACES,
        reason="collecting_places_failed",
        dependency=STEP_COLLECTING_PLACES,
    )
    snapshot = refresh_import_job_snapshot(db_session, city_id=city.id, source="import_pipeline_failed")
    db_session.refresh(job)

    assert snapshot["data_coverage"]["places_total"] >= 1
    assert job.step_details["admin_import_snapshot"]["source"] == "import_pipeline_failed"


@pytest.mark.parametrize(
    "message",
    [
        "psycopg.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block",
        "current transaction is aborted",
    ],
)
def test_is_aborted_transaction_error_detector_new(message: str) -> None:
    assert is_aborted_transaction_error(Exception(message)) is True
