from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.admin_operation import AdminOperation

OPERATION_TYPE = "backlog_reduction"
FULL_RUN_CODE = "full_safe_queue_run"
ACTIVE_STATUSES = {"running", "stop_requested"}
TERMINAL_STATUSES = {"completed", "partial", "failed", "stopped"}
STALE_AFTER = timedelta(minutes=10)
SAFE_QUEUE_ACTIONS = (
    "enqueue_photo_discovery",
    "enqueue_address_recovery",
    "enqueue_description_enrichment",
    "auto_recheck_verification_backlog",
)
ACTION_TITLES = {
    "enqueue_photo_discovery": "Фото",
    "enqueue_address_recovery": "Адреса",
    "enqueue_description_enrichment": "Описания",
    "auto_recheck_verification_backlog": "Перепроверка данных",
}


def create_full_run(db: Session, *, actor: str) -> dict[str, Any]:
    active = _latest_active_operation(db)
    if active is not None and not _is_stale(active):
        payload = _payload(active)
        payload["was_created"] = False
        return payload
    now = datetime.utcnow()
    operation = AdminOperation(
        operation_type=OPERATION_TYPE,
        status="running",
        actor=actor or "admin",
        city_slug=None,
        place_ids=[],
        result={
            "action_code": FULL_RUN_CODE,
            "title": "Полный безопасный прогон",
            "actor": actor or "admin",
            "started_at": now.isoformat(),
            "finished_at": None,
            "last_heartbeat_at": now.isoformat(),
            "status_label": "Выполняется",
            "stop_requested": False,
            "total_actions": len(SAFE_QUEUE_ACTIONS),
            "processed_actions": 0,
            "remaining_actions": len(SAFE_QUEUE_ACTIONS),
            "affected_count": 0,
            "changed_count": 0,
            "queued_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "remaining_count": len(SAFE_QUEUE_ACTIONS),
            "actions": [
                {
                    "action_code": code,
                    "title": ACTION_TITLES[code],
                    "status": "pending",
                    "affected_count": 0,
                    "changed_count": 0,
                    "queued_count": 0,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "started_at": None,
                    "finished_at": None,
                    "message": None,
                }
                for code in SAFE_QUEUE_ACTIONS
            ],
        },
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    payload = _payload(operation)
    payload["was_created"] = True
    return payload


def latest_full_run(db: Session) -> dict[str, Any] | None:
    operation = _latest_operation(db)
    return _payload(operation) if operation else None


def read_full_run(db: Session, job_id: int) -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    return _payload(operation)


def should_stop(db: Session, job_id: int) -> bool:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return True
    result = dict(operation.result or {})
    return bool(result.get("stop_requested")) or operation.status == "stopped"


def mark_step_running(db: Session, job_id: int, action_code: str) -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    if operation.status in TERMINAL_STATUSES:
        return _payload(operation)
    if action_code not in SAFE_QUEUE_ACTIONS:
        return _payload(operation)
    now = datetime.utcnow()
    result = dict(operation.result or {})
    actions = list(result.get("actions") or [])
    for action in actions:
        if action.get("action_code") == action_code:
            action["status"] = "running"
            action["started_at"] = action.get("started_at") or now.isoformat()
            break
    operation.status = "running"
    result["actions"] = actions
    result["status_label"] = f"Выполняется: {ACTION_TITLES.get(action_code, action_code)}"
    result["last_heartbeat_at"] = now.isoformat()
    operation.result = result
    db.commit()
    db.refresh(operation)
    return _payload(operation)


def record_step_result(db: Session, job_id: int, action_code: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    if action_code not in SAFE_QUEUE_ACTIONS:
        return _payload(operation)
    now = datetime.utcnow()
    result = dict(operation.result or {})
    actions = list(result.get("actions") or [])
    for action in actions:
        if action.get("action_code") == action_code:
            action.update({
                "status": payload.get("status") or "completed",
                "affected_count": _to_int(payload.get("affected_count")),
                "changed_count": _to_int(payload.get("changed_count")),
                "queued_count": _to_int(payload.get("queued_count")),
                "skipped_count": _to_int(payload.get("skipped_count")),
                "failed_count": _to_int(payload.get("failed_count")),
                "message": payload.get("message"),
                "job_id": payload.get("job_id"),
                "audit_id": payload.get("audit_id"),
                "finished_at": now.isoformat(),
            })
            break
    result["actions"] = actions
    _recompute(result, now)
    operation.result = result
    db.commit()
    db.refresh(operation)
    return _payload(operation)


def record_step_error(db: Session, job_id: int, action_code: str, message: str) -> dict[str, Any] | None:
    return record_step_result(db, job_id, action_code, {"status": "failed", "failed_count": 1, "message": message})


def complete_full_run(db: Session, job_id: int) -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    result = dict(operation.result or {})
    now = datetime.utcnow()
    failed = _to_int(result.get("failed_count"))
    operation.status = "partial" if failed else "completed"
    result["status_label"] = "Завершён с ошибками" if failed else "Завершён"
    result["finished_at"] = now.isoformat()
    result["last_heartbeat_at"] = now.isoformat()
    result["remaining_actions"] = len([a for a in result.get("actions", []) if a.get("status") in {"pending", "running"}])
    result["remaining_count"] = result["remaining_actions"]
    operation.result = result
    db.commit()
    db.refresh(operation)
    return _payload(operation)


def finalize_stopped(db: Session, job_id: int, *, label: str = "Остановлен оператором") -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    now = datetime.utcnow()
    result = dict(operation.result or {})
    result["finished_at"] = now.isoformat()
    result["last_heartbeat_at"] = now.isoformat()
    result["status_label"] = label
    result["stop_requested"] = True
    actions = list(result.get("actions") or [])
    for action in actions:
        if action.get("status") == "running":
            action["status"] = "stopped"
            action["finished_at"] = action.get("finished_at") or now.isoformat()
    result["actions"] = actions
    _recompute(result, now)
    operation.status = "stopped"
    operation.result = result
    db.commit()
    db.refresh(operation)
    return _payload(operation)


def mark_stop_requested(db: Session, job_id: int, *, actor: str) -> dict[str, Any] | None:
    operation = _get_operation(db, job_id)
    if operation is None or _action_code(operation) != FULL_RUN_CODE:
        return None
    result = dict(operation.result or {})
    now = datetime.utcnow()
    was_stale = _is_stale(operation)
    result["stop_requested"] = True
    result["stop_requested_at"] = now.isoformat()
    result["stop_requested_by"] = actor or "admin"
    result["last_heartbeat_at"] = now.isoformat()
    if operation.status in TERMINAL_STATUSES:
        operation.result = result
        db.commit()
        db.refresh(operation)
        return _payload(operation)
    if was_stale:
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


def _recompute(result: dict[str, Any], now: datetime) -> None:
    actions = list(result.get("actions") or [])
    done = {"applied", "completed", "partial", "failed", "unsupported", "stopped"}
    processed = len([a for a in actions if a.get("status") in done])
    result["processed_actions"] = processed
    result["remaining_actions"] = max(0, len(actions) - processed)
    result["remaining_count"] = result["remaining_actions"]
    result["affected_count"] = sum(_to_int(a.get("affected_count")) for a in actions)
    result["changed_count"] = sum(_to_int(a.get("changed_count")) for a in actions)
    result["queued_count"] = sum(_to_int(a.get("queued_count")) for a in actions)
    result["skipped_count"] = sum(_to_int(a.get("skipped_count")) for a in actions)
    result["failed_count"] = sum(_to_int(a.get("failed_count")) for a in actions)
    result["last_heartbeat_at"] = now.isoformat()


def _latest_operation(db: Session) -> AdminOperation | None:
    candidates = db.query(AdminOperation).filter(AdminOperation.operation_type == OPERATION_TYPE).order_by(AdminOperation.id.desc()).limit(50).all()
    return next((operation for operation in candidates if _action_code(operation) == FULL_RUN_CODE), None)


def _latest_active_operation(db: Session) -> AdminOperation | None:
    candidates = db.query(AdminOperation).filter(AdminOperation.operation_type == OPERATION_TYPE).order_by(AdminOperation.id.desc()).limit(50).all()
    return next((operation for operation in candidates if _action_code(operation) == FULL_RUN_CODE and operation.status in ACTIVE_STATUSES), None)


def _get_operation(db: Session, job_id: int) -> AdminOperation | None:
    return db.query(AdminOperation).filter(AdminOperation.id == job_id, AdminOperation.operation_type == OPERATION_TYPE).first()


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
