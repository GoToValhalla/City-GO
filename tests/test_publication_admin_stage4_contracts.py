from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect

import models.publication_admin_stage4  # noqa: F401
from db.base import Base
from services.publication_admin_guard_service import (
    BulkOperationValidationError,
    KillSwitchBlockedError,
    PublicationTransitionError,
    RollbackValidationError,
    assert_bulk_apply_allowed,
    assert_not_blocked_by_kill_switch,
    assert_rollback_request_valid,
    assert_transition_allowed,
)
from tests.allure_support import title


STAGE4_TABLES = {
    "publication_transition_rules",
    "quality_gate_rules",
    "rollback_requests",
    "admin_bulk_operations",
    "admin_kill_switches",
}


@title("Stage 4 metadata содержит таблицы Publication/Admin")
def test_stage4_metadata_contains_publication_admin_tables() -> None:
    assert STAGE4_TABLES <= set(Base.metadata.tables)


@title("Stage 4 test database создаёт таблицы Publication/Admin")
def test_stage4_database_contains_publication_admin_tables(engine) -> None:
    assert STAGE4_TABLES <= set(inspect(engine).get_table_names())


@title("PublicationTransitionRule содержит state machine contract")
def test_publication_transition_rule_contract_columns() -> None:
    columns = set(Base.metadata.tables["publication_transition_rules"].columns.keys())

    assert {
        "entity_type",
        "from_state",
        "to_state",
        "required_role",
        "required_quality_gate",
        "is_destructive",
        "status",
    } <= columns


@title("QualityGateRule содержит metric/operator/threshold contract")
def test_quality_gate_rule_contract_columns() -> None:
    columns = set(Base.metadata.tables["quality_gate_rules"].columns.keys())

    assert {
        "gate_code",
        "entity_type",
        "metric_name",
        "operator",
        "threshold_value",
        "severity",
        "failure_message",
        "status",
    } <= columns


@title("RollbackRequest требует target snapshot, actor and reason")
def test_rollback_request_contract_columns() -> None:
    columns = set(Base.metadata.tables["rollback_requests"].columns.keys())

    assert {
        "target_type",
        "target_id",
        "target_snapshot_version",
        "source_event_id",
        "requested_by",
        "reason",
        "status",
        "payload",
    } <= columns


@title("AdminBulkOperation хранит dry-run/apply contract")
def test_admin_bulk_operation_contract_columns() -> None:
    columns = set(Base.metadata.tables["admin_bulk_operations"].columns.keys())

    assert {
        "operation_type",
        "target_filter",
        "mode",
        "dry_run_operation_id",
        "actor",
        "reason",
        "status",
        "affected_count",
        "skipped_count",
        "failed_count",
        "result_payload",
    } <= columns


@title("AdminKillSwitch хранит scope/action/actor/reason/expiry contract")
def test_admin_kill_switch_contract_columns() -> None:
    columns = set(Base.metadata.tables["admin_kill_switches"].columns.keys())

    assert {"switch_scope", "target", "action", "actor", "reason", "status", "expires_at"} <= columns


@title("Publication transition helper блокирует неразрешённый переход")
def test_publication_transition_helper_blocks_forbidden_transition() -> None:
    assert_transition_allowed(from_state="approved", to_state="published", allowed_pairs={("approved", "published")})

    with pytest.raises(PublicationTransitionError):
        assert_transition_allowed(from_state="draft", to_state="published", allowed_pairs={("approved", "published")})


@title("Rollback helper требует actor, reason and target version")
def test_rollback_helper_requires_actor_reason_and_snapshot_version() -> None:
    assert_rollback_request_valid(actor="admin", reason="bad publish", target_snapshot_version=2)

    with pytest.raises(RollbackValidationError):
        assert_rollback_request_valid(actor="admin", reason="", target_snapshot_version=2)

    with pytest.raises(RollbackValidationError):
        assert_rollback_request_valid(actor="admin", reason="bad publish", target_snapshot_version=0)


@title("Bulk apply helper требует dry-run operation id and reason")
def test_bulk_apply_helper_requires_dry_run_and_reason() -> None:
    assert_bulk_apply_allowed(mode="dry_run", dry_run_operation_id=None, reason="preview")
    assert_bulk_apply_allowed(mode="apply", dry_run_operation_id=1, reason="approved bulk action")

    with pytest.raises(BulkOperationValidationError):
        assert_bulk_apply_allowed(mode="apply", dry_run_operation_id=None, reason="approved bulk action")

    with pytest.raises(BulkOperationValidationError):
        assert_bulk_apply_allowed(mode="apply", dry_run_operation_id=1, reason="")


@title("Kill switch helper блокирует активное действие и игнорирует expired switch")
def test_kill_switch_helper_blocks_active_action() -> None:
    now = datetime.utcnow()

    with pytest.raises(KillSwitchBlockedError):
        assert_not_blocked_by_kill_switch(
            action="publication",
            switch_action="publication",
            switch_status="active",
            expires_at=now + timedelta(hours=1),
            now=now,
        )

    assert_not_blocked_by_kill_switch(
        action="publication",
        switch_action="publication",
        switch_status="active",
        expires_at=now - timedelta(hours=1),
        now=now,
    )
