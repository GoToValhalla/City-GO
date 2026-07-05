from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.admin_operation import AdminOperation

OPERATION_TYPE = "backlog_reduction"
FULL_RUN_CODE = "full_safe_queue_run"
ACTIVE_STATUSES = {"running", "stop_requested"}
STALE_AFTER = timedelta(minutes=10)


def latest_full_run(db: Session) -> dict[str, Any] | None:
    operation = _latest_operation(db)
    return _payload(operation) if operation else None


def read_full_run(db: Session, job_id: int) -> dict[str, Any] | None:
    operation = db.query(AdminOperation).filter(AdminOperation.id == job_id, AdminOperation.operation_type == OPERATION_TYPE).first()
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    return _payload(operation)


def mark_stop_requested(db: Session, job_id: int, *, actor: str) -> dict[str, Any] | None:
    operation = db.query(AdminOperation).filter(AdminOperation.id == job_id, AdminOperation.operation_type == OPERATION_TYPE).first()
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    result = dict(operation.result or {})
    now = datetime.utcnow()
    result["stop_requested"] = True
    result["stop_requested_at"] = now.isoformat()
    result["stop_requested_by"] = actor or "admin"
    result["last_heartbeat_at"] = now.isoformat()
    if operation.status in ACTIVE_STATUSES and _is_stale(operation):
        operation.status = "stopped"
        result["finished_at"] = now.isoformat()
        result["status_label"] = "Остановлен после отсутствия прогресса"
    elif operation.status in ACTIVE_STATUSES:
        operation.status = "stop_requested"
        result["status_label"] = "Остановка запрошена"
    operation.result = result
    db.commit()
    db.refresh(operation)
    return _payload(operation)


def _latest_operation(db: Session) -> AdminOperation | None:
    candidates = db.query(AdminOperation).filter(AdminOperation.operation_type == OPERATION_TYPE).order_by(AdminOperation.id.desc()).limit(50).all()
    return next((operation for operation in candidates if _action_code(operation) == FULL_RUN_CODE), None)


def _payload(operation: AdminOperation) -> dict[str, Any]:
    result = dict(operation.result or {})
    stale = operation.status in ACTIVE_STATUSES and _is_stale(operation)
    return {
        "job_id": operation.id,
        "status": operation.status,
        "runtime_status": "stuck" if stale else operation.status,
        "is_running": operation.status in ACTIVE_STATUSES,
        "is_stale": stale,
        "created_at": operation.created_at,
        "updated_at": operation.updated_at,
        "actor": operation.actor,
        "action_code": result.get("action_code") or FULL_RUN_CODE,
        "status_label": result.get("status_label"),
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
        "last_heartbeat_at": result.get("last_heartbeat_at"),
        "total_actions": _to_int(result.get("total_actions")),
        "processed_actions": _to_int(result.get("processed_actions")),
        "remaining_actions": _to_int(result.get("remaining_actions")),
        "affected_count": _to_int(result.get("affected_count")),
        "changed_count": _to_int(result.get("changed_count")),
        "queued_count": _to_int(result.get("queued_count")),
        "skipped_count": _to_int(result.get("skipped_count")),
        "failed_count": _to_int(result.get("failed_count")),
        "remaining_count": _to_int(result.get("remaining_count")),
        "stop_requested": bool(result.get("stop_requested")),
        "actions": result.get("actions") or [],
    }


def _action_code(operation: AdminOperation) -> str:
    return str((operation.result or {}).get("action_code") or "")


def _is_stale(operation: AdminOperation) -> bool:
    heartbeat = _parse_dt((operation.result or {}).get("last_heartbeat_at")) or operation.updated_at or operation.created_at
    return datetime.utcnow() - heartbeat > STALE_AFTER


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
