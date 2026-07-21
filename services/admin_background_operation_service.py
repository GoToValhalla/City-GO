"""Shared durable background-operation queue for heavy admin jobs."""

from __future__ import annotations

import os
import socket
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy import and_, or_, update
from sqlalchemy.exc import IntegrityError
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

# Bounded lease: a "running" row whose lease has expired is presumed
# crashed/orphaned and becomes reclaimable. MAX_ATTEMPTS bounds retries so a
# permanently-failing operation type cannot loop forever between "running"
# (stale) and reclaim.
LEASE_DURATION = timedelta(minutes=10)
MAX_ATTEMPTS = 3


def _worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def create_background_operation(
    db: Session,
    *,
    operation_type: str,
    actor: str,
    city_slug: str | None = None,
    params: dict[str, object] | None = None,
) -> AdminOperation:
    """Insert one durable job; the DB partial unique index arbitrates races."""
    normalized_city = str(city_slug).strip() if city_slug else None
    op = AdminOperation(
        operation_type=operation_type,
        status="queued",
        actor=actor,
        city_slug=normalized_city,
        place_ids=[],
        result=params or {},
        attempt_count=0,
    )
    db.add(op)
    try:
        db.commit()
        db.refresh(op)
        return op
    except IntegrityError:
        db.rollback()
        existing = active_operation(db, operation_type=operation_type, city_slug=normalized_city)
        if existing is None:
            raise
        return existing


def get_operation(db: Session, operation_id: int) -> AdminOperation | None:
    return db.query(AdminOperation).filter(AdminOperation.id == operation_id).first()


def active_operation(
    db: Session,
    *,
    operation_type: str,
    city_slug: str | None = None,
) -> AdminOperation | None:
    query = db.query(AdminOperation).filter(
        AdminOperation.operation_type == operation_type,
        AdminOperation.status.in_(RUNNING_STATUSES),
    )
    if city_slug is None:
        query = query.filter(AdminOperation.city_slug.is_(None))
    else:
        query = query.filter(AdminOperation.city_slug == city_slug)
    return query.order_by(AdminOperation.created_at.asc(), AdminOperation.id.asc()).first()


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
        "attempt_count": op.attempt_count,
        "worker_id": op.worker_id,
        "claimed_at": op.claimed_at.isoformat() if op.claimed_at else None,
        "lease_expires_at": op.lease_expires_at.isoformat() if op.lease_expires_at else None,
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


def claim_next_background_operation(db: Session, *, now: datetime | None = None) -> int | None:
    """Atomically claim one queued row, or one stale `running` row whose
    lease expired (the worker that held it presumably crashed after claim).

    Rows that already exhausted MAX_ATTEMPTS are terminalized as `failed`
    instead of being reclaimed again, so a permanently-failing operation
    cannot loop forever between "running" (stale) and reclaim.
    """
    current = now or datetime.utcnow()
    candidate = (
        db.query(AdminOperation.id, AdminOperation.status, AdminOperation.attempt_count)
        .filter(
            or_(
                AdminOperation.status == "queued",
                and_(
                    AdminOperation.status == "running",
                    AdminOperation.lease_expires_at.isnot(None),
                    AdminOperation.lease_expires_at < current,
                ),
            )
        )
        .order_by(AdminOperation.created_at.asc(), AdminOperation.id.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if candidate is None:
        db.rollback()
        return None
    operation_id = int(candidate[0])
    previous_status = str(candidate[1])
    attempt_count = int(candidate[2] or 0)

    if previous_status == "running" and attempt_count >= MAX_ATTEMPTS:
        db.execute(
            update(AdminOperation)
            .where(AdminOperation.id == operation_id, AdminOperation.status == "running")
            .values(
                status="failed",
                error_message=f"Exceeded max attempts ({MAX_ATTEMPTS}) after stale lease reclaim",
                updated_at=current,
            )
        )
        db.commit()
        return None

    next_attempt = attempt_count + 1
    claimed = db.execute(
        update(AdminOperation)
        .where(AdminOperation.id == operation_id, AdminOperation.status == previous_status)
        .values(
            status="running",
            claimed_at=current,
            lease_expires_at=current + LEASE_DURATION,
            attempt_count=next_attempt,
            worker_id=_worker_identity(),
            updated_at=current,
        )
    ).rowcount
    if claimed != 1:
        db.rollback()
        return None
    db.commit()
    return operation_id


def run_queued_background_operations(*, limit: int = 1, session_factory: Callable[[], Session] = SessionLocal) -> int:
    processed = 0
    for _ in range(max(1, limit)):
        with session_factory() as claim_db:
            operation_id = claim_next_background_operation(claim_db)
        if operation_id is None:
            break
        run_background_operation(operation_id, session_factory=session_factory, already_claimed=True)
        processed += 1
    return processed


def run_background_operation(
    operation_id: int,
    session_factory: Callable[[], Session] = SessionLocal,
    *,
    already_claimed: bool = False,
) -> None:
    db = session_factory()
    try:
        op = get_operation(db, operation_id)
        if op is None:
            return
        if not already_claimed:
            claimed_id = claim_next_background_operation(db)
            if claimed_id != operation_id:
                return
            db.refresh(op)
        elif op.status != "running":
            return

        runner = _runner_for(op.operation_type)
        if runner is None:
            op.status = "failed"
            op.error_message = f"Unsupported admin operation type: {op.operation_type}"
            op.updated_at = datetime.utcnow()
            db.commit()
            return
        try:
            result = runner(db, op)
            op.status = "completed"
            op.result = result
            op.error_message = None
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            op = get_operation(db, operation_id)
            if op is None:
                return
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
