from __future__ import annotations

import pytest
from sqlalchemy import text

from sqlalchemy.exc import SQLAlchemyError

from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.import_pipeline import runner as import_runner
from services.import_pipeline.schema_compat import (
    collecting_has_schema_failure,
    diagnose_import_schema_gaps,
    ensure_import_pipeline_schema,
    is_schema_mismatch_error,
)
from services.import_pipeline.steps import STEP_COLLECTING_PLACES, STEP_FINDING_IMAGES
from services.import_pipeline.transaction import verify_session_usable


def test_is_schema_mismatch_error_detects_undefined_column_new() -> None:
    message = 'psycopg.errors.UndefinedColumn: column places.place_layer does not exist'
    assert is_schema_mismatch_error(message) is True


def test_ensure_import_pipeline_schema_creates_place_field_provenance_new(db_session) -> None:
    bind = db_session.get_bind()
    gaps_before = diagnose_import_schema_gaps(bind.engine)
    bind.execute(text("DROP TABLE IF EXISTS place_field_provenance"))
    gaps = diagnose_import_schema_gaps(bind.engine)
    assert "place_field_provenance" in gaps["missing_tables"]

    result = ensure_import_pipeline_schema(bind.engine)

    assert "place_field_provenance" in result["created_tables"]
    gaps_after = diagnose_import_schema_gaps(bind.engine)
    assert gaps_after["missing_tables"] == []
    assert gaps_before["missing_place_columns"] == []


def test_collecting_schema_failure_skips_finding_images_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="schema-skip-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="schema-skip-place", title="Schema Skip", lat=54.7, lng=20.5, category="park")
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
    monkeypatch.setattr(
        import_runner,
        "run_image_enrich",
        lambda *_args, **_kwargs: image_calls.append("images") or {"scanned_places": 1, "created": 0, "failed": 0},
    )
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {"readiness_score": 0.2})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    job = db_session.get(CityAdminImportJob, job.id)

    assert image_calls == []
    assert result["images"]["status"] == "skipped"
    assert result["images"]["reason"] == "dependency_failed"
    assert collecting_has_schema_failure(result["import"]) is True
    assert verify_session_usable(db_session) is True
    assert any(
        item.get("step") == STEP_COLLECTING_PLACES and schema_error in str(item.get("error"))
        for item in job.step_details["warnings"]
    )
    assert not any("InFailedSqlTransaction" in str(item) for item in job.step_details["warnings"] if item.get("step") == STEP_FINDING_IMAGES)


def test_undefined_column_in_collecting_triggers_rollback_without_poison_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="schema-rollback-city", launch_status="published", is_active=True)
    place = Place(city_id=city.id, slug="schema-rollback-place", title="Schema Rollback", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()
    original_error = "food_area: psycopg.errors.UndefinedColumn: column places.primary_destination_id does not exist"
    recovery_calls: list[str] = []
    query_calls = {"count": 0}
    original_query = db_session.query

    def _fake_recover(db, job: CityAdminImportJob, *, step: str, error: BaseException | None = None) -> dict[str, object]:
        recovery_calls.append(step)
        return {
            "step": "transaction_isolation",
            "status": "rolled_back",
            "after_step": step,
            "reason": "db_error_recovered",
            "session_usable": True,
            "rolled_back": True,
            "error": str(error)[:1000] if error else None,
        }

    def _query_with_poison(*args, **kwargs):
        model = args[0] if args else None
        if model is Place and query_calls["count"] == 0:
            query_calls["count"] += 1
            raise SQLAlchemyError("psycopg.errors.UndefinedColumn: column places.primary_destination_id does not exist")
        return original_query(*args, **kwargs)

    monkeypatch.setattr(import_runner, "recover_after_db_error", _fake_recover)
    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(
        import_runner,
        "summarize_import_results",
        lambda _payload: {
            "scopes_total": 2,
            "scopes_succeeded": 0,
            "places_found": 0,
            "places_saved": 0,
            "status": "failed",
            "last_error": original_error,
            "scope_errors": [{"scope": "food_area", "error": original_error, "kind": "schema_mismatch"}],
        },
    )
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_args, **_kwargs: {"checked": 0, "updated": 0, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 0, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_args, **_kwargs: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(db_session, "query", _query_with_poison)

    result = import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)

    assert recovery_calls == [STEP_COLLECTING_PLACES]
    assert result["import"]["last_error"] == original_error
    assert result["images"]["status"] == "skipped"
    assert verify_session_usable(db_session) is True


def test_diagnose_reports_missing_source_observations_columns_new(db_session) -> None:
    bind = db_session.get_bind()
    bind.execute(text("ALTER TABLE source_observations RENAME COLUMN source_license TO source_license_bak"))
    try:
        gaps = diagnose_import_schema_gaps(bind.engine)
        assert "source_license" in gaps["missing_source_observation_columns"]
    finally:
        bind.execute(text("ALTER TABLE source_observations RENAME COLUMN source_license_bak TO source_license"))


def test_existing_source_observations_schema_reports_no_gaps_new(db_session) -> None:
    bind = db_session.get_bind()
    gaps = diagnose_import_schema_gaps(bind.engine)
    assert gaps["missing_source_observation_columns"] == []


def test_ensure_import_pipeline_schema_repairs_source_observations_before_collection_new() -> None:
    """Simulates the pre-migration production table (columns never shipped) on a fresh engine,
    since SQLite can't drop indexed/constrained columns from an already-migrated table in place."""
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE source_observations ("
                "id INTEGER PRIMARY KEY, import_batch_id INTEGER NOT NULL, city_id INTEGER NOT NULL, "
                "scope_id INTEGER, source_type VARCHAR(64) NOT NULL, source_external_id VARCHAR(128) NOT NULL, "
                "source_object_type VARCHAR(64), source_url VARCHAR(1000), raw_name VARCHAR(255), "
                "raw_category VARCHAR(128), raw_lat FLOAT, raw_lng FLOAT, raw_payload JSON, "
                "payload_hash VARCHAR(128) NOT NULL, first_seen_at DATETIME, last_seen_at DATETIME, "
                "seen_in_batch_id INTEGER, canonical_place_id INTEGER, match_status VARCHAR(64) NOT NULL, "
                "normalization_status VARCHAR(64) NOT NULL, rejection_reason VARCHAR(128), confidence FLOAT, "
                "created_at DATETIME, updated_at DATETIME"
                ")"
            )
        )

    gaps_before = diagnose_import_schema_gaps(engine)
    assert set(gaps_before["missing_source_observation_columns"]) == {"source_license", "attribution_text", "idempotency_key"}

    result = ensure_import_pipeline_schema(engine)

    assert set(result["added_columns"]) >= {
        "source_observations.source_license",
        "source_observations.attribution_text",
        "source_observations.idempotency_key",
    }
    gaps_after = diagnose_import_schema_gaps(engine)
    assert gaps_after["missing_source_observation_columns"] == []
