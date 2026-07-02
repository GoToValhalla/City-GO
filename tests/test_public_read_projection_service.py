from __future__ import annotations

import pytest
from sqlalchemy import inspect

import models.search_routing_stage5  # noqa: F401
from db.base import Base
from services.public_read_projection_service import (
    PublicReadProjectionError,
    assert_projection_fresh,
    build_projection_rebuild_summary,
    build_route_candidate_set,
    build_routing_node_from_snapshot,
    build_search_document_from_snapshot,
    choose_public_read_path,
    is_projection_stale,
)
from tests.allure_support import title


STAGE_5_TABLES = {
    "search_place_documents",
    "routing_place_nodes",
    "route_candidate_sets",
    "projection_rebuild_jobs",
}


@title("Public Read Projections metadata содержит Stage 5 таблицы")
def test_public_read_projection_metadata_contains_stage5_tables() -> None:
    assert STAGE_5_TABLES <= set(Base.metadata.tables)


@title("Public Read Projections test database создаёт Stage 5 таблицы")
def test_public_read_projection_database_contains_stage5_tables(engine) -> None:
    assert STAGE_5_TABLES <= set(inspect(engine).get_table_names())


@title("Stage 5 projection tables содержат read model columns")
def test_stage5_projection_table_contract_columns() -> None:
    search_columns = set(Base.metadata.tables["search_place_documents"].columns.keys())
    routing_columns = set(Base.metadata.tables["routing_place_nodes"].columns.keys())
    candidates_columns = set(Base.metadata.tables["route_candidate_sets"].columns.keys())
    job_columns = set(Base.metadata.tables["projection_rebuild_jobs"].columns.keys())

    assert {"place_id", "city_id", "source_snapshot_version", "is_public", "is_search_visible", "freshness_status"} <= search_columns
    assert {"place_id", "city_id", "source_snapshot_version", "lat", "lng", "is_route_visible", "freshness_status"} <= routing_columns
    assert {"city_id", "profile", "route_policy", "source_snapshot_version", "candidate_count", "payload"} <= candidates_columns
    assert {"projection_type", "status", "source_snapshot_version", "processed_count", "rebuilt_count", "failed_count"} <= job_columns


@title("Public catalog search routing choose projection read path")
def test_public_read_paths_choose_projection_read_path() -> None:
    catalog = choose_public_read_path(
        read_path="public_catalog",
        projection_type="search_place_document",
        projection_count=3,
        source_snapshot_version=2,
        projection_snapshot_version=2,
    )
    search = choose_public_read_path(
        read_path="search",
        projection_type="search_place_document",
        projection_count=3,
        source_snapshot_version=2,
        projection_snapshot_version=2,
    )
    routing = choose_public_read_path(
        read_path="routing",
        projection_type="routing_place_node",
        projection_count=2,
        source_snapshot_version=2,
        projection_snapshot_version=2,
    )

    assert catalog.uses_projection is True
    assert search.uses_projection is True
    assert routing.uses_projection is True
    assert catalog.reason == "projection_ready"


@title("Public read path blocks empty and stale projections")
def test_public_read_path_blocks_empty_and_stale_projections() -> None:
    with pytest.raises(PublicReadProjectionError):
        choose_public_read_path(
            read_path="public_catalog",
            projection_type="search_place_document",
            projection_count=0,
            source_snapshot_version=2,
            projection_snapshot_version=2,
        )
    with pytest.raises(PublicReadProjectionError):
        choose_public_read_path(
            read_path="search",
            projection_type="search_place_document",
            projection_count=1,
            source_snapshot_version=3,
            projection_snapshot_version=2,
        )

    fallback = choose_public_read_path(
        read_path="search",
        projection_type="search_place_document",
        projection_count=0,
        source_snapshot_version=2,
        projection_snapshot_version=2,
        fallback_allowed=True,
    )
    assert fallback.uses_projection is False
    assert fallback.reason == "projection_empty_fallback_allowed"


@title("Projection freshness helper detects version and status drift")
def test_projection_freshness_helper_detects_version_and_status_drift() -> None:
    assert is_projection_stale(source_snapshot_version=5, projection_snapshot_version=5, freshness_status="fresh") is False
    assert is_projection_stale(source_snapshot_version=5, projection_snapshot_version=4, freshness_status="fresh") is True
    assert is_projection_stale(source_snapshot_version=5, projection_snapshot_version=5, freshness_status="stale") is True
    assert is_projection_stale(source_snapshot_version=None, projection_snapshot_version=5, freshness_status="fresh") is True

    assert_projection_fresh(source_snapshot_version=5, projection_snapshot_version=5, freshness_status="fresh")
    with pytest.raises(PublicReadProjectionError):
        assert_projection_fresh(source_snapshot_version=5, projection_snapshot_version=4, freshness_status="fresh")


@title("Search document builder maps published snapshot into search projection")
def test_search_document_builder_maps_snapshot_into_search_projection() -> None:
    document = build_search_document_from_snapshot(
        snapshot={
            "place_id": 101,
            "city_id": 10,
            "snapshot_version": 3,
            "title": "Central Park",
            "description": "Main city park",
            "category": "park",
            "tags": ["nature", "walk"],
            "is_public": True,
            "is_searchable": True,
            "ranking_score": 8.5,
        },
        locale="en",
    )

    assert document["source_snapshot_version"] == 3
    assert document["locale"] == "en"
    assert document["is_search_visible"] is True
    assert "Central Park" in document["searchable_text"]
    assert document["tags_payload"] == {"tags": ["nature", "walk"]}

    non_public = build_search_document_from_snapshot(
        snapshot={"place_id": 101, "city_id": 10, "snapshot_version": 3, "is_public": False, "is_searchable": True}
    )
    assert non_public["is_search_visible"] is False

    with pytest.raises(PublicReadProjectionError):
        build_search_document_from_snapshot(snapshot={"place_id": 1})


@title("Routing node builder and candidate set keep only route visible nodes")
def test_routing_node_builder_and_candidate_set_keep_only_route_visible_nodes() -> None:
    visible_node = build_routing_node_from_snapshot(
        snapshot={
            "place_id": 101,
            "city_id": 10,
            "snapshot_version": 3,
            "lat": 43.2389,
            "lng": 76.8897,
            "is_public": True,
            "is_route_eligible": True,
            "quality_score": 92,
        }
    )
    non_public_node = build_routing_node_from_snapshot(
        snapshot={
            "place_id": 102,
            "city_id": 10,
            "snapshot_version": 3,
            "lat": 43.24,
            "lng": 76.88,
            "is_public": False,
            "is_route_eligible": True,
        }
    )
    candidate_set = build_route_candidate_set(
        city_id=10,
        profile="overview",
        route_policy="city_walking",
        source_snapshot_version=3,
        routing_nodes=[visible_node, non_public_node],
    )

    assert visible_node["is_route_visible"] is True
    assert non_public_node["is_route_visible"] is False
    assert candidate_set["candidate_count"] == 1
    assert candidate_set["payload"] == {"place_ids": [101]}

    with pytest.raises(PublicReadProjectionError):
        build_routing_node_from_snapshot(snapshot={"place_id": 1, "city_id": 10, "snapshot_version": 3})


@title("Projection rebuild summary exposes status and counters")
def test_projection_rebuild_summary_exposes_status_and_counters() -> None:
    succeeded = build_projection_rebuild_summary(
        projection_type="route_candidate_set",
        source_snapshot_version=3,
        processed_count=10,
        rebuilt_count=8,
        skipped_count=2,
    )
    failed = build_projection_rebuild_summary(
        projection_type="search_place_document",
        source_snapshot_version=3,
        processed_count=10,
        rebuilt_count=7,
        failed_count=1,
        error_summary="one row failed",
    )

    assert succeeded["status"] == "succeeded"
    assert succeeded["skipped_count"] == 2
    assert failed["status"] == "failed"
    assert failed["failed_count"] == 1
    assert failed["error_summary"] == "one row failed"

    with pytest.raises(PublicReadProjectionError):
        build_projection_rebuild_summary(
            projection_type="legacy_places",
            source_snapshot_version=3,
            processed_count=1,
            rebuilt_count=0,
        )
