from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect

import models.search_routing_stage5  # noqa: F401
import models.service_extraction_stage6  # noqa: F401
from db.base import Base
from services.projection_and_extraction_guard_service import (
    ExtractionReadinessError,
    ProjectionFreshnessError,
    assert_extraction_ready,
    assert_projection_fresh,
    assert_projection_reads_snapshot,
)
from tests.allure_support import title


STAGE5_TABLES = {
    "search_place_documents",
    "routing_place_nodes",
    "route_candidate_sets",
    "projection_rebuild_jobs",
}

STAGE6_TABLES = {
    "module_boundaries",
    "extraction_candidates",
    "integration_contracts",
    "strangler_adapters",
}


@title("Stage 5 metadata содержит search/routing projection таблицы")
def test_stage5_metadata_contains_projection_tables() -> None:
    assert STAGE5_TABLES <= set(Base.metadata.tables)


@title("Stage 5 test database создаёт search/routing projection таблицы")
def test_stage5_database_contains_projection_tables(engine) -> None:
    assert STAGE5_TABLES <= set(inspect(engine).get_table_names())


@title("SearchPlaceDocument содержит public search projection contract")
def test_search_place_document_contract_columns() -> None:
    columns = set(Base.metadata.tables["search_place_documents"].columns.keys())

    assert {
        "place_id",
        "city_id",
        "source_snapshot_version",
        "locale",
        "title",
        "searchable_text",
        "category",
        "tags_payload",
        "is_public",
        "is_search_visible",
        "ranking_score",
        "freshness_status",
        "built_at",
    } <= columns


@title("RoutingPlaceNode содержит routing read model contract")
def test_routing_place_node_contract_columns() -> None:
    columns = set(Base.metadata.tables["routing_place_nodes"].columns.keys())

    assert {
        "place_id",
        "city_id",
        "source_snapshot_version",
        "lat",
        "lng",
        "category",
        "route_policy",
        "average_visit_duration_minutes",
        "is_route_visible",
        "quality_score",
        "freshness_status",
        "built_at",
    } <= columns


@title("RouteCandidateSet и ProjectionRebuildJob содержат projection rebuild contract")
def test_candidate_set_and_rebuild_job_contract_columns() -> None:
    candidate_columns = set(Base.metadata.tables["route_candidate_sets"].columns.keys())
    job_columns = set(Base.metadata.tables["projection_rebuild_jobs"].columns.keys())

    assert {"city_id", "profile", "route_policy", "source_snapshot_version", "candidate_count", "payload", "freshness_status"} <= candidate_columns
    assert {"projection_type", "city_id", "status", "source_snapshot_version", "processed_count", "rebuilt_count", "skipped_count", "failed_count", "error_summary"} <= job_columns


@title("Projection helpers требуют snapshot version и свежесть")
def test_projection_helpers_require_snapshot_and_freshness() -> None:
    now = datetime.utcnow()

    assert_projection_reads_snapshot(source_snapshot_version=1)
    assert_projection_fresh(built_at=now - timedelta(minutes=5), max_age_minutes=10, now=now)

    with pytest.raises(ProjectionFreshnessError):
        assert_projection_reads_snapshot(source_snapshot_version=0)

    with pytest.raises(ProjectionFreshnessError):
        assert_projection_fresh(built_at=now - timedelta(minutes=20), max_age_minutes=10, now=now)


@title("Stage 6 metadata содержит service extraction таблицы")
def test_stage6_metadata_contains_extraction_tables() -> None:
    assert STAGE6_TABLES <= set(Base.metadata.tables)


@title("Stage 6 test database создаёт service extraction таблицы")
def test_stage6_database_contains_extraction_tables(engine) -> None:
    assert STAGE6_TABLES <= set(inspect(engine).get_table_names())


@title("ModuleBoundary содержит boundary ownership contract")
def test_module_boundary_contract_columns() -> None:
    columns = set(Base.metadata.tables["module_boundaries"].columns.keys())

    assert {"module_code", "owner", "source_of_truth_tables", "allowed_dependencies", "emitted_events", "consumed_events", "status"} <= columns


@title("ExtractionCandidate содержит readiness contract")
def test_extraction_candidate_contract_columns() -> None:
    columns = set(Base.metadata.tables["extraction_candidates"].columns.keys())

    assert {
        "module_code",
        "target_service_name",
        "owner",
        "readiness_status",
        "api_contract_ref",
        "event_contract_ref",
        "data_migration_plan_ref",
        "rollback_plan_ref",
        "is_enabled",
    } <= columns


@title("IntegrationContract и StranglerAdapter содержат extraction integration contract")
def test_integration_contract_and_strangler_adapter_columns() -> None:
    contract_columns = set(Base.metadata.tables["integration_contracts"].columns.keys())
    adapter_columns = set(Base.metadata.tables["strangler_adapters"].columns.keys())

    assert {"producer", "consumer", "protocol", "schema_ref", "version", "compatibility_policy", "status"} <= contract_columns
    assert {"source_module", "target_service", "adapter_mode", "read_strategy", "write_strategy", "fallback_strategy", "status"} <= adapter_columns


@title("Extraction readiness helper блокирует incomplete extraction")
def test_extraction_readiness_helper_blocks_incomplete_extraction() -> None:
    assert_extraction_ready(
        owner="platform",
        api_contract_ref="docs/api/catalog.md",
        event_contract_ref="docs/events/catalog.md",
        data_migration_plan_ref="docs/migrations/catalog.md",
        rollback_plan_ref="docs/rollback/catalog.md",
    )

    with pytest.raises(ExtractionReadinessError):
        assert_extraction_ready(
            owner="platform",
            api_contract_ref="docs/api/catalog.md",
            event_contract_ref=None,
            data_migration_plan_ref="docs/migrations/catalog.md",
            rollback_plan_ref="docs/rollback/catalog.md",
        )
