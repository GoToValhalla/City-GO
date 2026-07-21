"""Shared durable background-operation queue for heavy admin jobs.

Lease/fencing model: every claim or reclaim increments `lease_generation`
(a fencing token) and returns it to the caller alongside the operation id.
While the runner executes, a background heartbeat thread periodically
renews `lease_expires_at` through a short-lived, independent DB session
(never the runner's own session/transaction) via an atomic
`UPDATE ... WHERE id = :id AND lease_generation = :generation`. If another
worker has since reclaimed the row (because this worker's lease actually
did expire, e.g. a long GC pause), that UPDATE's WHERE clause matches zero
rows, the heartbeat detects it lost fencing and stops, and the original
worker's eventual terminal write is fenced the same way -- so it can never
clobber the new owner's state. This is what makes lease *renewal* safe
without ever holding one transaction open for the entire runner execution:
the "am I still the legitimate owner" check and the "extend my time" write
are the same atomic, short statement, repeated on an interval.
"""

from __future__ import annotations

import contextlib
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Iterator

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

# Bounded lease: a "running" row whose lease has expired AND whose heartbeat
# has stopped renewing it is presumed crashed/orphaned and becomes
# reclaimable. A live worker renews well before expiry (HEARTBEAT_INTERVAL
# << LEASE_DURATION), so a legitimately running operation's lease never
# actually reaches expiry. MAX_ATTEMPTS bounds retries so a
# permanently-failing operation type cannot loop forever between "running"
# (stale) and reclaim.
LEASE_DURATION = timedelta(minutes=10)
HEARTBEAT_INTERVAL = timedelta(seconds=30)
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


def claim_next_background_operation(db: Session, *, now: datetime | None = None) -> tuple[int, int] | None:
    """Atomically claim one queued row, or one stale `running` row whose
    lease expired (the worker that held it presumably crashed after claim).

    Returns (operation_id, lease_generation) on success. lease_generation is
    a fencing token, incremented on every claim/reclaim: the caller must
    pass it back to every subsequent renew_lease/finalize write for this
    attempt, so a worker whose lease has already been reclaimed by someone
    else can never again successfully write to the row.

    Rows that already exhausted MAX_ATTEMPTS are terminalized as `failed`
    instead of being reclaimed again, so a permanently-failing operation
    cannot loop forever between "running" (stale) and reclaim.
    """
    current = now or datetime.utcnow()
    candidate = (
        db.query(
            AdminOperation.id,
            AdminOperation.status,
            AdminOperation.attempt_count,
            AdminOperation.lease_generation,
        )
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
    previous_generation = int(candidate[3] or 0)

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
    next_generation = previous_generation + 1
    claimed = db.execute(
        update(AdminOperation)
        .where(AdminOperation.id == operation_id, AdminOperation.status == previous_status)
        .values(
            status="running",
            claimed_at=current,
            lease_expires_at=current + LEASE_DURATION,
            attempt_count=next_attempt,
            worker_id=_worker_identity(),
            lease_generation=next_generation,
            updated_at=current,
        )
    ).rowcount
    if claimed != 1:
        db.rollback()
        return None
    db.commit()
    return operation_id, next_generation


def renew_lease(
    operation_id: int,
    lease_generation: int,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    now: datetime | None = None,
) -> bool:
    """Atomically extend the lease for one specific claim attempt.

    Fenced by lease_generation: if another worker has since reclaimed this
    row (incrementing lease_generation), this UPDATE matches zero rows and
    returns False -- the caller must stop treating itself as the owner.
    Uses its own short session/transaction, never the runner's own long-
    running one, so no transaction is held open across runner execution.
    """
    current = now or datetime.utcnow()
    db = session_factory()
    try:
        updated = db.execute(
            update(AdminOperation)
            .where(
                AdminOperation.id == operation_id,
                AdminOperation.lease_generation == lease_generation,
                AdminOperation.status == "running",
            )
            .values(lease_expires_at=current + LEASE_DURATION, updated_at=current)
        ).rowcount
        db.commit()
        return updated == 1
    finally:
        db.close()


def finalize_background_operation(
    operation_id: int,
    lease_generation: int,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    status: str,
    result: dict[str, object] | None = None,
    error_message: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Fenced terminal write: only succeeds if lease_generation still
    matches, so a worker that lost its lease mid-run can never overwrite
    whatever the new owner has since written."""
    current = now or datetime.utcnow()
    values: dict[str, object] = {
        "status": status,
        "error_message": error_message,
        "updated_at": current,
    }
    if result is not None:
        values["result"] = result
    db = session_factory()
    try:
        updated = db.execute(
            update(AdminOperation)
            .where(
                AdminOperation.id == operation_id,
                AdminOperation.lease_generation == lease_generation,
            )
            .values(**values)
        ).rowcount
        db.commit()
        return updated == 1
    finally:
        db.close()


class _LeaseHeartbeat:
    """Background thread that periodically renews a claimed lease through
    its own independent session, while the runner executes in the caller's
    thread on its own (separate) session. Never shares a connection or
    transaction with the runner, so the runner's own DB work is never
    blocked by, or blocking, the heartbeat."""

    def __init__(
        self,
        operation_id: int,
        lease_generation: int,
        *,
        session_factory: Callable[[], Session],
        interval: timedelta = HEARTBEAT_INTERVAL,
    ) -> None:
        self._operation_id = operation_id
        self._lease_generation = lease_generation
        self._session_factory = session_factory
        self._interval_seconds = interval.total_seconds()
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def lost(self) -> bool:
        return self._lost.is_set()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(5.0, self._interval_seconds))

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            if self._lost.is_set():
                return
            renewed = renew_lease(
                self._operation_id, self._lease_generation, session_factory=self._session_factory
            )
            if not renewed:
                self._lost.set()
                return


@contextlib.contextmanager
def _lease_heartbeat(
    operation_id: int,
    lease_generation: int,
    *,
    session_factory: Callable[[], Session],
    interval: timedelta = HEARTBEAT_INTERVAL,
) -> Iterator[_LeaseHeartbeat]:
    heartbeat = _LeaseHeartbeat(operation_id, lease_generation, session_factory=session_factory, interval=interval)
    heartbeat.start()
    try:
        yield heartbeat
    finally:
        heartbeat.stop()


def run_queued_background_operations(*, limit: int = 1, session_factory: Callable[[], Session] = SessionLocal) -> int:
    processed = 0
    for _ in range(max(1, limit)):
        with session_factory() as claim_db:
            claimed = claim_next_background_operation(claim_db)
        if claimed is None:
            break
        operation_id, lease_generation = claimed
        _execute_claimed_operation(operation_id, lease_generation, session_factory=session_factory)
        processed += 1
    return processed


def run_background_operation(
    operation_id: int,
    session_factory: Callable[[], Session] = SessionLocal,
    *,
    already_claimed: bool = False,
) -> None:
    """Public entrypoint. If not already_claimed, this call performs its own
    claim/reclaim attempt first (which may legitimately claim a DIFFERENT
    stale row than operation_id, or claim nothing) -- callers relying on
    already_claimed=False must only use this for "claim whatever is next,"
    not "guarantee this exact row runs."""
    if already_claimed:
        db = session_factory()
        try:
            op = get_operation(db, operation_id)
            if op is None or op.status != "running":
                return
            lease_generation = op.lease_generation
        finally:
            db.close()
        _execute_claimed_operation(operation_id, lease_generation, session_factory=session_factory)
        return

    claim_db = session_factory()
    try:
        claimed = claim_next_background_operation(claim_db)
    finally:
        claim_db.close()
    if claimed is None or claimed[0] != operation_id:
        return
    _execute_claimed_operation(claimed[0], claimed[1], session_factory=session_factory)


def _execute_claimed_operation(
    operation_id: int,
    lease_generation: int,
    *,
    session_factory: Callable[[], Session],
    heartbeat_interval: timedelta | None = None,
) -> None:
    """Run the runner for one already-claimed (operation_id, lease_generation)
    attempt. A background heartbeat renews the lease on its own independent
    session/transaction for the whole duration; the runner's own session is
    never used for lease bookkeeping, and no transaction spans the entire
    runner call. The terminal write is fenced by lease_generation, so it is
    silently dropped (not applied) if this worker's lease was reclaimed by
    someone else in the meantime -- duplicate execution can still happen in
    the sense that two workers may both run to completion, but only one
    terminal write can ever land, and it is always the most recent
    legitimate owner's.

    heartbeat_interval defaults to the module-level HEARTBEAT_INTERVAL, read
    at call time (not baked into a function signature default), so tests
    can shrink LEASE_DURATION/HEARTBEAT_INTERVAL via monkeypatch and have it
    actually take effect here."""
    interval = heartbeat_interval if heartbeat_interval is not None else HEARTBEAT_INTERVAL
    db = session_factory()
    try:
        op = get_operation(db, operation_id)
        if op is None:
            return
        runner = _runner_for(op.operation_type)
        if runner is None:
            finalize_background_operation(
                operation_id,
                lease_generation,
                session_factory=session_factory,
                status="failed",
                error_message=f"Unsupported admin operation type: {op.operation_type}",
            )
            return

        with _lease_heartbeat(
            operation_id, lease_generation, session_factory=session_factory, interval=interval
        ) as heartbeat:
            try:
                result = runner(db, op)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                write_system_log(
                    db,
                    level="error",
                    module="admin_background_operation",
                    message=str(exc),
                    city_slug=op.city_slug,
                    request_id=str(op.id),
                    commit=True,
                )
                if heartbeat.lost:
                    return
                finalize_background_operation(
                    operation_id,
                    lease_generation,
                    session_factory=session_factory,
                    status="failed",
                    error_message=str(exc),
                )
                return

        if heartbeat.lost:
            # Another worker already reclaimed this row (this worker's
            # lease genuinely expired mid-run); the fenced UPDATE below
            # would be a no-op anyway, but skip it explicitly for clarity
            # and to avoid writing a misleadingly "successful" result that
            # nobody will ever read as authoritative.
            return
        finalize_background_operation(
            operation_id,
            lease_generation,
            session_factory=session_factory,
            status="completed",
            result=result,
            error_message=None,
        )
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
