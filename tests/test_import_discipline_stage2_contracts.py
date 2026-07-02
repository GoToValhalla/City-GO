from __future__ import annotations

import pytest
from sqlalchemy import inspect

import models.import_discipline_stage2  # noqa: F401
from db.base import Base
from services.import_discipline_service import (
    assert_import_update_does_not_touch_publication_state,
    build_import_idempotency_key,
    payload_hash,
)
from tests.allure_support import title


STAGE2_TABLES = {
    "import_runs",
    "import_run_batches",
    "import_dead_letter_items",
    "import_conflict_candidates",
}


@title("Stage 2 metadata содержит таблицы Import Discipline")
def test_stage2_metadata_contains_import_discipline_tables() -> None:
    table_names = set(Base.metadata.tables)

    assert STAGE2_TABLES <= table_names


@title("Stage 2 test database создаёт таблицы Import Discipline")
def test_stage2_database_contains_import_discipline_tables(engine) -> None:
    table_names = set(inspect(engine).get_table_names())

    assert STAGE2_TABLES <= table_names


@title("ImportRun содержит status/checkpoint/counter/quality поля")
def test_import_run_contract_columns() -> None:
    table = Base.metadata.tables["import_runs"]
    columns = set(table.columns.keys())

    assert {
        "run_key",
        "city_id",
        "scope_id",
        "provider",
        "run_type",
        "status",
        "checkpoint_payload",
        "quality_summary",
        "processed_count",
        "created_count",
        "matched_count",
        "rejected_count",
        "failed_count",
        "error_summary",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("run_key",) in unique_columns


@title("ImportRunBatch содержит cursor/status/checkpoint/counter поля")
def test_import_run_batch_contract_columns() -> None:
    table = Base.metadata.tables["import_run_batches"]
    columns = set(table.columns.keys())

    assert {
        "import_run_id",
        "batch_key",
        "provider_cursor",
        "status",
        "checkpoint_payload",
        "processed_count",
        "created_count",
        "matched_count",
        "rejected_count",
        "failed_count",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("import_run_id", "batch_key") in unique_columns


@title("ImportDeadLetterItem содержит replay/error payload поля")
def test_import_dead_letter_contract_columns() -> None:
    table = Base.metadata.tables["import_dead_letter_items"]
    columns = set(table.columns.keys())

    assert {
        "import_run_id",
        "import_batch_id",
        "source_observation_id",
        "payload_hash",
        "payload_reference",
        "payload_json",
        "error_class",
        "error_message",
        "replay_status",
        "replay_attempts",
        "last_replay_at",
    } <= columns


@title("ImportConflictCandidate содержит evidence/score/status поля")
def test_import_conflict_candidate_contract_columns() -> None:
    table = Base.metadata.tables["import_conflict_candidates"]
    columns = set(table.columns.keys())

    assert {
        "import_run_id",
        "source_observation_id",
        "matched_place_id",
        "conflict_type",
        "conflict_score",
        "evidence_payload",
        "resolution_status",
        "resolved_by",
        "resolved_at",
        "resolution_reason",
    } <= columns


@title("Import idempotency key детерминированный и зависит от provider/external_id/hash")
def test_import_idempotency_key_is_deterministic() -> None:
    key1 = build_import_idempotency_key(provider="osm", external_id="node-1", payload_hash="abc")
    key2 = build_import_idempotency_key(provider="osm", external_id="node-1", payload_hash="abc")
    key3 = build_import_idempotency_key(provider="osm", external_id="node-2", payload_hash="abc")

    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 64


@title("Payload hash стабилен при разном порядке ключей")
def test_payload_hash_is_stable_for_key_order() -> None:
    assert payload_hash({"b": 2, "a": 1}) == payload_hash({"a": 1, "b": 2})


@title("Import write guard запрещает менять publication state")
def test_import_update_guard_blocks_publication_fields() -> None:
    with pytest.raises(ValueError):
        assert_import_update_does_not_touch_publication_state({"title", "publication_status"})

    assert_import_update_does_not_touch_publication_state({"raw_payload", "payload_hash"})
