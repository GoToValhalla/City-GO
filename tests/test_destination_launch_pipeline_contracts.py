from __future__ import annotations

import pytest
from sqlalchemy import inspect

import models.destination_launch_pipeline  # noqa: F401
from db.base import Base
from services.destination_launch_pipeline_service import (
    REQUIRED_DESTINATION_LAUNCH_CHECKLIST_ITEMS,
    DestinationLaunchReadinessError,
    DestinationLaunchTransitionError,
    DestinationPublishGateError,
    DestinationRouteReadyError,
    assert_destination_publishable,
    assert_destination_route_ready,
    assert_launch_can_go_live,
    assert_launch_transition_allowed,
    calculate_launch_readiness_percent,
    missing_required_launch_items,
)
from tests.allure_support import title


DESTINATION_LAUNCH_TABLES = {
    "destination_launch_states",
    "destination_launch_pipeline_runs",
    "destination_launch_steps",
    "destination_launch_checklist_items",
    "destination_launch_events",
    "destination_readiness_summaries",
}


COMPLETED_LAUNCH_CHECKLIST = {
    item_code: "completed"
    for item_code in REQUIRED_DESTINATION_LAUNCH_CHECKLIST_ITEMS
}


@title("Destination Launch metadata содержит все таблицы pipeline")
def test_destination_launch_metadata_contains_tables() -> None:
    assert DESTINATION_LAUNCH_TABLES <= set(Base.metadata.tables)


@title("Destination Launch test database создаёт все таблицы pipeline")
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


@title("DestinationLaunchChecklistItem содержит live checklist contract")
def test_destination_launch_checklist_item_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_launch_checklist_items"].columns.keys())

    assert {
        "city_id",
        "pipeline_run_id",
        "item_code",
        "status",
        "is_required_for_live",
        "evidence_payload",
        "blocking_reason",
        "completed_by",
        "completed_at",
        "created_at",
    } <= columns


@title("DestinationLaunchEvent содержит append-only timeline contract")
def test_destination_launch_event_contract_columns() -> None:
    columns = set(Base.metadata.tables["destination_launch_events"].columns.keys())

    assert {
        "city_id",
        "pipeline_run_id",
        "event_type",
        "previous_status",
        "next_status",
        "actor",
        "reason",
        "event_payload",
        "created_at",
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


@title("Destination launch required checklist фиксирует live gate порядок")
def test_destination_launch_required_checklist_contract() -> None:
    assert REQUIRED_DESTINATION_LAUNCH_CHECKLIST_ITEMS == (
        "import_scope_configured",
        "import_completed",
        "enrichment_completed",
        "quality_gate_passed",
        "review_queue_empty_or_accepted",
        "publication_approved",
        "projections_rebuilt",
        "route_smoke_passed",
    )


@title("Destination launch readiness percent считает только completed required items")
def test_destination_launch_readiness_percent_counts_completed_required_items() -> None:
    assert calculate_launch_readiness_percent({}) == 0
    assert calculate_launch_readiness_percent({"import_scope_configured": "pending"}) == 0
    assert calculate_launch_readiness_percent({"import_scope_configured": "completed"}) == 12

    half_completed = {
        "import_scope_configured": "completed",
        "import_completed": "completed",
        "enrichment_completed": "completed",
        "quality_gate_passed": "completed",
        "review_queue_empty_or_accepted": "pending",
        "publication_approved": "pending",
        "projections_rebuilt": "pending",
        "route_smoke_passed": "pending",
        "non_required_note": "completed",
    }
    assert calculate_launch_readiness_percent(half_completed) == 50
    assert calculate_launch_readiness_percent(COMPLETED_LAUNCH_CHECKLIST) == 100


@title("Destination launch missing helper возвращает отсутствующие required items")
def test_destination_launch_missing_required_items_are_ordered() -> None:
    missing_items = missing_required_launch_items(
        {
            "import_scope_configured": "completed",
            "import_completed": "completed",
            "quality_gate_passed": "failed",
        }
    )

    assert missing_items == [
        "enrichment_completed",
        "quality_gate_passed",
        "review_queue_empty_or_accepted",
        "publication_approved",
        "projections_rebuilt",
        "route_smoke_passed",
    ]


@title("Destination launch transition helper разрешает linear path до live")
def test_destination_launch_transition_helper_allows_linear_path_to_live() -> None:
    allowed_path = (
        ("created", "import_pending"),
        ("import_pending", "importing"),
        ("importing", "enrichment_pending"),
        ("enrichment_pending", "enriching"),
        ("enriching", "readiness_pending"),
        ("readiness_pending", "review_required"),
        ("review_required", "publishable"),
        ("publishable", "published"),
        ("published", "projections_pending"),
        ("projections_pending", "route_ready"),
        ("route_ready", "live"),
    )

    for from_status, to_status in allowed_path:
        assert_launch_transition_allowed(from_status=from_status, to_status=to_status)


@title("Destination launch transition helper блокирует illegal state jump")
def test_destination_launch_transition_helper_blocks_illegal_jump() -> None:
    assert_launch_transition_allowed(from_status="created", to_status="import_pending")

    with pytest.raises(DestinationLaunchTransitionError):
        assert_launch_transition_allowed(from_status="created", to_status="published")

    with pytest.raises(DestinationLaunchTransitionError):
        assert_launch_transition_allowed(from_status="published", to_status="live")


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


@title("Destination live gate требует route_ready, completed checklist and passed smoke")
def test_destination_live_gate_requires_route_ready_completed_checklist_and_passed_smoke() -> None:
    assert_launch_can_go_live(
        launch_status="route_ready",
        checklist_statuses=COMPLETED_LAUNCH_CHECKLIST,
        route_smoke_status="passed",
    )

    with pytest.raises(DestinationLaunchReadinessError):
        assert_launch_can_go_live(
            launch_status="published",
            checklist_statuses=COMPLETED_LAUNCH_CHECKLIST,
            route_smoke_status="passed",
        )

    incomplete_checklist = dict(COMPLETED_LAUNCH_CHECKLIST)
    incomplete_checklist["publication_approved"] = "pending"
    with pytest.raises(DestinationLaunchReadinessError):
        assert_launch_can_go_live(
            launch_status="route_ready",
            checklist_statuses=incomplete_checklist,
            route_smoke_status="passed",
        )

    with pytest.raises(DestinationLaunchReadinessError):
        assert_launch_can_go_live(
            launch_status="route_ready",
            checklist_statuses=COMPLETED_LAUNCH_CHECKLIST,
            route_smoke_status="failed",
        )
