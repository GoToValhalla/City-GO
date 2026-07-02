from __future__ import annotations

from sqlalchemy import inspect

# Explicit import registers Stage 1 models even if a future import registry is refactored.
import models.data_foundation_stage1  # noqa: F401
import models.place_published_snapshot  # noqa: F401
from db.base import Base
from tests.allure_support import title


STAGE1_TABLES = {
    "source_observations",
    "place_fact_versions",
    "ai_task_runs",
    "ai_candidates",
    "review_decisions",
    "publication_events",
    "published_place_snapshots",
}


@title("Stage 1 metadata содержит все таблицы Data Foundation")
def test_stage1_metadata_contains_data_foundation_tables() -> None:
    table_names = set(Base.metadata.tables)

    assert STAGE1_TABLES <= table_names


@title("Stage 1 test database создаёт все таблицы Data Foundation")
def test_stage1_database_contains_data_foundation_tables(engine) -> None:
    table_names = set(inspect(engine).get_table_names())

    assert STAGE1_TABLES <= table_names


@title("SourceObservation хранит idempotency и source attribution")
def test_source_observation_has_idempotency_and_attribution_columns() -> None:
    table = Base.metadata.tables["source_observations"]
    columns = set(table.columns.keys())

    assert {
        "source_type",
        "source_external_id",
        "source_license",
        "attribution_text",
        "idempotency_key",
        "payload_hash",
        "raw_payload",
        "canonical_place_id",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("idempotency_key",) in unique_columns
    assert ("source_type", "source_external_id") in unique_columns


@title("PlaceFactVersion хранит версионированный факт с locale/source/confidence/status")
def test_place_fact_version_has_fact_versioning_contract() -> None:
    table = Base.metadata.tables["place_fact_versions"]
    columns = set(table.columns.keys())

    assert {
        "place_id",
        "field_name",
        "locale",
        "version",
        "value_json",
        "source_type",
        "source_ref",
        "confidence",
        "status",
        "superseded_by_id",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("place_id", "field_name", "locale", "version") in unique_columns


@title("AiTaskRun фиксирует prompt/model/cost/latency")
def test_ai_task_run_has_prompt_model_cost_contract() -> None:
    table = Base.metadata.tables["ai_task_runs"]
    columns = set(table.columns.keys())

    assert {
        "task_type",
        "model_provider",
        "model_name",
        "prompt_version",
        "prompt_hash",
        "input_hash",
        "output_json",
        "tokens_in",
        "tokens_out",
        "cost_amount",
        "latency_ms",
        "status",
    } <= columns


@title("AiCandidate остаётся candidate и связан с AiTaskRun/PlaceFactVersion")
def test_ai_candidate_links_task_and_fact_without_public_flags() -> None:
    table = Base.metadata.tables["ai_candidates"]
    columns = set(table.columns.keys())

    assert {
        "ai_task_run_id",
        "place_id",
        "field_name",
        "locale",
        "value_json",
        "confidence",
        "validation_result_json",
        "status",
        "place_fact_version_id",
    } <= columns

    assert "is_published" not in columns
    assert "is_public" not in columns


@title("ReviewDecision и PublicationEvent содержат actor/reason/state payload")
def test_review_and_publication_audit_contracts() -> None:
    review_columns = set(Base.metadata.tables["review_decisions"].columns.keys())
    event_columns = set(Base.metadata.tables["publication_events"].columns.keys())

    assert {"target_type", "target_id", "decision", "reason", "actor", "previous_value_json", "new_value_json"} <= review_columns
    assert {"event_type", "previous_state", "next_state", "actor", "reason", "snapshot_version", "payload_json"} <= event_columns


@title("PublishedPlaceSnapshot является public read projection")
def test_published_place_snapshot_has_public_projection_contract() -> None:
    table = Base.metadata.tables["published_place_snapshots"]
    columns = set(table.columns.keys())

    assert {
        "place_id",
        "city_id",
        "snapshot_version",
        "locale",
        "publication_status",
        "is_public",
        "is_catalog_visible",
        "is_search_visible",
        "is_route_visible",
        "snapshot_payload",
        "quality_payload",
        "media_payload",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("place_id", "snapshot_version") in unique_columns
