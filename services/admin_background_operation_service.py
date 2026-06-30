"""Shared background operation service for heavy admin jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.admin_operation import AdminOperation
from services.coverage_readiness_gate import apply_coverage_readiness_gate
from services.city_readiness import recalculate_city_readiness_snapshot
from services.data_coverage_assurance import run_data_coverage_assurance
from services.system_log_service import write_system_log

OperationRunner = Callable[[Session, AdminOperation], dict[str, object]]

OP_COVERAGE_GAPS_REFRESH = "coverage_gaps_refresh"
OP_CITY_READINESS_RECALCULATE = "city_readiness_recalculate"
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
RUNNING_STATUSES = {"queued", "running"}
DEFAULT_STALE_AFTER_HOURS = 24


def create_background_operation(
    db: Session,
    *,
    operation_type: str,
    actor: str,
    city_slug: str | None = None,
    params: dict[str, object] | None = None,
) -> AdminOperation:
    existing = latest_operation(db, operation_type=operation_type, city_slug=city_slug)
    if existing is not None and existing.status in RUNNING_STATUSES:
        return existing
    op = AdminOperation(
        operation_type=operation_type,
        status="queued",
        actor=actor,
        city_slug=city_slug,
        place_ids=[],
        result=params or {},
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def get_operation(db: Session, operation_id: int) -> AdminOperation | None:
    return db.query(AdminOperation).filter(AdminOperation.id == operation_id).first()


def latest_operation(
    db: Session,
    *,
    operation_type: str,
    city_slug: str | None = None,
) -> AdminOperation | None:
    query = db.query(AdminOperation).filter(AdminOperation.operation_type == operation_type)
    if city_slug:
        query = query.filter(AdminOperation.city_slug == city_slug)
    return query.order_by(AdminOperation.created_at.desc(), AdminOperation.id.desc()).first()


def operation_payload(op: AdminOperation | None) -> dict[str, object] | None:
    if op is None:
        return None
    return {
        "id": op.id,
        "operation_id": op.id,
        "operation_type": op.operation_type,
        "status": op.status,
        "actor": op.actor,
        "city_slug": op.city_slug,
        "result": op.result or {},
        "error": op.error_message,
        "created_at": op.created_at.isoformat() if op.created_at else None,
        "updated_at": op.updated_at.isoformat() if op.updated_at else None,
        "running": op.status in RUNNING_STATUSES,
        "terminal": op.status in TERMINAL_STATUSES,
    }


def snapshot_status_payload(
    *,
    last_snapshot_at: datetime | None,
    latest: AdminOperation | None,
    stale_after_hours: int = DEFAULT_STALE_AFTER_HOURS,
) -> dict[str, object]:
    now = datetime.utcnow()
    is_stale = last_snapshot_at is None or last_snapshot_at < now - timedelta(hours=stale_after_hours)
    running = latest is not None and latest.status in RUNNING_STATUSES
    failed = latest is not None and latest.status == "failed"
    if running:
        freshness = "running"
    elif failed and is_stale:
        freshness = "failed_stale"
    elif is_stale:
        freshness = "stale"
    else:
        freshness = "fresh"
    return {
        "last_snapshot_at": last_snapshot_at.isoformat() if last_snapshot_at else None,
        "freshness": freshness,
        "is_stale": is_stale,
        "latest_operation": operation_payload(latest),
    }


def run_background_operation(operation_id: int) -> None:
    db = SessionLocal()
    try:
        op = get_operation(db, operation_id)
        if op is None:
            return
        runner = _runner_for(op.operation_type)
        if runner is None:
            op.status = "failed"
            op.error_message = f"Unsupported admin operation type: {op.operation_type}"
            op.updated_at = datetime.utcnow()
            db.commit()
            return
        op.status = "running"
        op.updated_at = datetime.utcnow()
        db.commit()
        try:
            result = runner(db, op)
            op.status = "completed"
            op.result = result
            op.error_message = None
        except Exception as exc:  # noqa: BLE001
            op.status = "failed"
            op.error_message = str(exc)
            write_system_log(
                db,
                level="error",
                module="admin_background_operation",
                message=str(exc),
                city_slug=op.city_slug,
                request_id=str(op.id),
                commit=False,
            )
        op.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def _runner_for(operation_type: str) -> OperationRunner | None:
    return {
        OP_COVERAGE_GAPS_REFRESH: _run_coverage_gaps_refresh,
        OP_CITY_READINESS_RECALCULATE: _run_city_readiness_recalculate,
    }.get(operation_type)


def _run_coverage_gaps_refresh(db: Session, op: AdminOperation) -> dict[str, object]:
    result = run_data_coverage_assurance(db, city_slug=op.city_slug)
    gate = apply_coverage_readiness_gate(db, city_slug=op.city_slug)
    db.commit()
    return {"status": "success", **result, "readiness_gate": gate}


def _run_city_readiness_recalculate(db: Session, op: AdminOperation) -> dict[str, object]:
    params: dict[str, Any] = op.result or {}
    city_slug = op.city_slug or str(params.get("city_slug") or "")
    if not city_slug:
        raise ValueError("city_slug is required")
    payload = recalculate_city_readiness_snapshot(
        db,
        city_slug=city_slug,
        reason=str(params.get("reason") or "admin_background_city_readiness_recalculation"),
        recalculate_place_scores=params.get("recalculate_place_scores") is not False,
    )
    if payload is None:
        raise ValueError("Город не найден")
    return payload
