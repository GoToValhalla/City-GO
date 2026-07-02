from __future__ import annotations

import pytest
from sqlalchemy import inspect

import models.destination_launch_pipeline  # noqa: F401
from db.base import Base
from services.destination_launch_pipeline_service import (
    DestinationLaunchTransitionError,
    DestinationPublishGateError,
    DestinationRouteReadyError,
    assert_destination_publishable,
    assert_destination_route_ready,
    assert_launch_transition_allowed,
)
from tests.allure_support import title


DESTINATION_LAUNCH_TABLES = {
    "destination_launch_states",
    "destination_launch_pipeline_runs",
    "destination_launch_steps",
    "destination_readiness_summaries",
}


@title("Destination Launch metadata содержит таблицы pipeline")
def test_destination_launch_metadata_contains_tables() -> None:
    assert DESTINATION_LAUNCH_TABLES <= set(Base.metadata.tables)


@title("Destination Launch test database создаёт таблицы pipeline")
def test_destination_launch_database_contains_tables(engine) -> None:
    assert DESTINATION_LAUNCH_TABLES <= set(inspect(engine).get_table_names())


@title("DestinationLaunchState содержит состояние, readiness и route flags")
def test_destination_launch_state_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_launch_states"].columns.keys())

    assert {
        "city_id",
        "destination_key",
        "launch_status",
        "current_step",
        "actor",
        "reason",
        "readiness_score",
        "blocking_reason",
        "is_published",
        "is_route_ready",
        "state_payload",
    } <= columns


@title("DestinationLaunchPipelineRun содержит status, trigger и counters")
def test_destination_launch_pipeline_run_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_launch_pipeline_runs"].columns.keys())

    assert {
        "city_id",
        "pipeline_key",
        "status",
        "requested_by",
        "trigger_source",
        "processed_steps_count",
        "failed_steps_count",
        "skipped_steps_count",
        "error_summary",
        "run_payload",
        "started_at",
        "finished_at",
    } <= columns


@title("DestinationLaunchStep содержит step payload and error contract")
def test_destination_launch_step_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_launch_steps"].columns.keys())

    assert {
        "pipeline_run_id",
        "step_key",
        "status",
        "input_payload",
        "output_payload",
        "error_summary",
        "started_at",
        "finished_at",
    } <= columns


@title("DestinationReadinessSummary содержит coverage, publish and route readiness")
def test_destination_readiness_summary_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_readiness_summaries"].columns.keys())

    assert {
        "city_id",
        "pipeline_run_id",
        "readiness_score",
        "places_total",
        "places_publishable",
        "places_route_eligible",
        "photo_coverage_pct",
        "address_coverage_pct",
        "hours_coverage_pct",
        "description_coverage_pct",
        "duplicate_candidates_count",
        "conflict_candidates_count",
        "blocking_issues",
        "is_publishable",
        "is_route_ready",
        "search_projection_ready",
        "routing_projection_ready",
    } <= columns


@title("Destination launch transition helper блокирует illegal state jump")
def test_destination_launch_transition_helper_blocks_illegal_jump() -> None:
    assert_launch_transition_allowed(from_status="created", to_status="import_pending")

    with pytest.raises(DestinationLaunchTransitionError):
        assert_launch_transition_allowed(from_status="created", to_status="published")


@title("Destination publish gate блокирует failed, low readiness and blockers")
def test_destination_publish_gate_blocks_unready_launch() -> None:
    assert_destination_publishable(
        launch_status="publishable",
        readiness_score=80,
        is_publishable=True,
        blocking_issues=None,
    )

    with pytest.raises(DestinationPublishGateError):
        assert_destination_publishable(
            launch_status="failed",
            readiness_score=90,
            is_publishable=True,
            blocking_issues=None,
        )

    with pytest.raises(DestinationPublishGateError):
        assert_destination_publishable(
            launch_status="publishable",
            readiness_score=60,
            is_publishable=True,
            blocking_issues=None,
        )

    with pytest.raises(DestinationPublishGateError):
        assert_destination_publishable(
            launch_status="publishable",
            readiness_score=90,
            is_publishable=True,
            blocking_issues={"missing_projection": True},
        )


@title("Destination route-ready gate требует публикацию, projections and 3+ route places")
def test_destination_route_ready_gate_requires_public_projections_and_places() -> None:
    assert_destination_route_ready(
        launch_status="projections_pending",
        is_published=True,
        search_projection_ready=True,
        routing_projection_ready=True,
        route_eligible_places=3,
    )

    with pytest.raises(DestinationRouteReadyError):
        assert_destination_route_ready(
            launch_status="projections_pending",
            is_published=False,
            search_projection_ready=True,
            routing_projection_ready=True,
            route_eligible_places=3,
        )

    with pytest.raises(DestinationRouteReadyError):
        assert_destination_route_ready(
            launch_status="projections_pending",
            is_published=True,
            search_projection_ready=True,
            routing_projection_ready=False,
            route_eligible_places=3,
        )

    with pytest.raises(DestinationRouteReadyError):
        assert_destination_route_ready(
            launch_status="projections_pending",
            is_published=True,
            search_projection_ready=True,
            routing_projection_ready=True,
            route_eligible_places=2,
        )
