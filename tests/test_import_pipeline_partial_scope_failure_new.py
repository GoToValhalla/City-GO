"""finding_images must only be treated as blocked when collecting_places
genuinely produced zero usable data this run — not whenever any single scope
fails while other scopes in the same run already succeeded and saved places."""

from __future__ import annotations

from sqlalchemy import text

from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.import_pipeline import runner as import_runner
from services.import_pipeline.schema_compat import collecting_has_schema_failure, diagnose_import_schema_gaps, ensure_import_pipeline_schema
from services.import_pipeline.steps import STEP_COLLECTING_PLACES


def test_missing_place_layer_column_reproduces_tourist_core_style_undefinedcolumn_new(db_session) -> None:
    """Reproduces the exact prod signature (psycopg UndefinedColumn on
    places.place_layer during tourist_core collection) and proves the existing
    self-heal (ensure_import_pipeline_schema, already run as a preflight before
    collecting_places) repairs it before any INSERT is attempted."""
    bind = db_session.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS ix_places_place_layer"))
    bind.execute(text("ALTER TABLE places DROP COLUMN place_layer"))

    gaps = diagnose_import_schema_gaps(bind.engine)
    assert "place_layer" in gaps["missing_place_columns"]

    from models.place import Place as PlaceModel

    try:
        db_session.query(PlaceModel.place_layer).first()
        assert False, "expected the drop to actually break the query"
    except Exception as exc:  # noqa: BLE001 - proving the real failure signature
        assert "place_layer" in str(exc) or "no such column" in str(exc).lower()

    result = ensure_import_pipeline_schema(bind.engine)

    assert "places.place_layer" in result["added_columns"]
    gaps_after = diagnose_import_schema_gaps(bind.engine)
    assert gaps_after["missing_place_columns"] == []
    db_session.expire_all()
    db_session.query(PlaceModel.place_layer).first()


def test_partial_scope_schema_failure_does_not_skip_finding_images_new(db_session, city_factory, monkeypatch) -> None:
    """Reproduces the Kaliningrad job #4 shape: tourist_core fails with
    schema_mismatch, but food_area/other scopes succeed and save real places —
    finding_images must still run against those places, not be skipped."""
    city = city_factory(slug="partial-scope-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="partial-scope-place", title="Partial Scope Place", lat=54.7, lng=20.5, category="cafe", image_url=None)
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    image_calls: list[str] = []
    schema_error = "tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist"

    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(
        import_runner,
        "summarize_import_results",
        lambda _payload: {
            "scopes_total": 3,
            "scopes_succeeded": 2,
            "places_found": 5,
            "places_saved": 5,
            "status": "partial_success",
            "last_error": schema_error,
            "scope_errors": [{"scope": "tourist_core", "error": schema_error, "kind": "schema_mismatch"}],
        },
    )
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(
        import_runner,
        "run_image_enrich",
        lambda *_args, **_kwargs: image_calls.append("images") or {"scanned_places": 1, "created": 0, "candidates_found": 0, "provider_status": "source_evidence_exhausted", "errors": []},
    )
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.5})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    job = db_session.get(CityAdminImportJob, job.id)

    assert image_calls == ["images"]
    assert result["images"].get("status") != "skipped"
    assert result["images"]["scanned_places"] == 1
    assert collecting_has_schema_failure(result["import"]) is True
    assert any(
        item.get("step") == STEP_COLLECTING_PLACES and schema_error in str(item.get("error"))
        for item in job.step_details["warnings"]
    )


def test_total_scope_failure_still_skips_finding_images_new(db_session, city_factory, monkeypatch) -> None:
    """Contrast case: when ALL scopes fail this run (scopes_succeeded=0), finding_images
    is still correctly skipped as dependency_failed, even if the city has pre-existing
    places from an earlier run — this run produced nothing new to justify scanning."""
    city = city_factory(slug="total-failure-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="total-failure-place", title="Total Failure Place", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    image_calls: list[str] = []
    schema_error = "tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist"

    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(
        import_runner,
        "summarize_import_results",
        lambda _payload: {
            "scopes_total": 3,
            "scopes_succeeded": 0,
            "places_found": 0,
            "places_saved": 0,
            "status": "failed",
            "last_error": schema_error,
            "scope_errors": [{"scope": "tourist_core", "error": schema_error, "kind": "schema_mismatch"}],
        },
    )
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: image_calls.append("images") or {"scanned_places": 1, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.2})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)

    assert image_calls == []
    assert result["images"]["status"] == "skipped"
    assert result["images"]["reason"] == "dependency_failed"
