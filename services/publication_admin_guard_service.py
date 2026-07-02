from __future__ import annotations

from datetime import datetime


class PublicationTransitionError(ValueError):
    pass


class RollbackValidationError(ValueError):
    pass


class BulkOperationValidationError(ValueError):
    pass


class KillSwitchBlockedError(ValueError):
    pass


def assert_transition_allowed(*, from_state: str, to_state: str, allowed_pairs: set[tuple[str, str]]) -> None:
    if (from_state, to_state) not in allowed_pairs:
        raise PublicationTransitionError(f"Transition is not allowed: {from_state} -> {to_state}")


def assert_rollback_request_valid(*, actor: str | None, reason: str | None, target_snapshot_version: int | None) -> None:
    if not actor:
        raise RollbackValidationError("Rollback requires actor")
    if not reason:
        raise RollbackValidationError("Rollback requires reason")
    if not target_snapshot_version or target_snapshot_version < 1:
        raise RollbackValidationError("Rollback requires target snapshot version")


def assert_bulk_apply_allowed(*, mode: str, dry_run_operation_id: int | None, reason: str | None) -> None:
    if mode == "apply" and not dry_run_operation_id:
        raise BulkOperationValidationError("Bulk apply requires dry-run operation id")
    if mode == "apply" and not reason:
        raise BulkOperationValidationError("Bulk apply requires reason")


def assert_not_blocked_by_kill_switch(
    *,
    action: str,
    switch_action: str,
    switch_status: str,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.utcnow()
    active = switch_status == "active" and (expires_at is None or expires_at > current_time)
    if active and switch_action in {action, "all"}:
        raise KillSwitchBlockedError(f"Action is blocked by kill switch: {action}")
