"""Real-connection PostgreSQL tests for the admin_operations bounded
lease/reclaim mechanism (services/admin_background_operation_service.py).

Root cause fixed: a job was committed as `running` before execution; if the
process died after claim, it stayed `running` forever, since the scheduler
only ever selects `queued` rows and the partial unique index on
(operation_type, city_slug) WHERE status IN ('queued','running') blocked any
replacement job for the same scope from ever being created.

These tests use two independent SessionLocal() connections (not the
rollback-wrapped tests/conftest.py fixture), matching
test_concurrent_worker_claim.py, because SQLite cannot reproduce
`FOR UPDATE SKIP LOCKED` races between genuinely separate connections.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

from db.session import SessionLocal
from models.admin_operation import AdminOperation
from services.admin_background_operation_service import (
    LEASE_DURATION,
    MAX_ATTEMPTS,
    claim_next_background_operation,
)

from conftest import unique_slug


def _make_operation(pg_session, **overrides) -> AdminOperation:
    defaults = dict(
        operation_type="coverage_gaps_refresh",
        status="queued",
        actor="test-actor",
        city_slug=unique_slug("lease-city"),
        place_ids=[],
        result={},
        attempt_count=0,
    )
    defaults.update(overrides)
    op = AdminOperation(**defaults)
    pg_session.add(op)
    pg_session.commit()
    pg_session.refresh(op)
    return op


def test_crash_after_claim_leaves_row_reclaimable_once_lease_expires_new(pg_session) -> None:
    """Simulates a worker that claimed a row and then crashed: status stays
    'running' with an expired lease. A later claim call must reclaim it."""
    op = _make_operation(pg_session)
    claimed_id = claim_next_background_operation(pg_session)
    assert claimed_id == op.id
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1

    # Simulate the lease having already expired (worker crashed, never renewed it).
    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).update(
        {"lease_expires_at": datetime.utcnow() - timedelta(seconds=1)}
    )
    pg_session.commit()

    reclaimed_id = claim_next_background_operation(pg_session)
    assert reclaimed_id == op.id
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2
    assert op.lease_expires_at > datetime.utcnow()

    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).delete()
    pg_session.commit()


def test_stale_running_operation_is_reclaimed_new(pg_session) -> None:
    """A 'running' row whose lease_expires_at is in the past is a valid
    reclaim candidate even without ever having gone through claim() first
    (e.g. a row hand-seeded as already-running by a crashed legacy worker)."""
    op = _make_operation(
        pg_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=50),
        attempt_count=1,
        worker_id="dead-worker:1234",
    )

    reclaimed_id = claim_next_background_operation(pg_session)
    assert reclaimed_id == op.id
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2
    assert op.worker_id != "dead-worker:1234"

    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).delete()
    pg_session.commit()


def test_non_stale_running_operation_is_not_reclaimed_new(pg_session) -> None:
    """A 'running' row with a lease still in the future must never be
    claimed by anyone else — the current worker is presumed alive."""
    op = _make_operation(
        pg_session,
        status="running",
        claimed_at=datetime.utcnow(),
        lease_expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempt_count=1,
        worker_id="alive-worker:5678",
    )

    reclaimed_id = claim_next_background_operation(pg_session)
    assert reclaimed_id is None
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1
    assert op.worker_id == "alive-worker:5678"

    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).delete()
    pg_session.commit()


def test_max_attempts_reached_terminalizes_instead_of_reclaiming_new(pg_session) -> None:
    """Once a stale 'running' row already used its last allowed attempt,
    the next claim call must mark it 'failed' and must not hand it out for
    another attempt — bounding retries so a permanently-crashing operation
    type cannot loop forever."""
    op = _make_operation(
        pg_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=50),
        attempt_count=MAX_ATTEMPTS,
    )

    reclaimed_id = claim_next_background_operation(pg_session)
    assert reclaimed_id is None
    pg_session.refresh(op)
    assert op.status == "failed"
    assert op.error_message is not None
    assert str(MAX_ATTEMPTS) in op.error_message

    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).delete()
    pg_session.commit()


def test_two_workers_racing_stale_reclaim_only_one_wins_new(pg_session) -> None:
    """Two workers concurrently attempting to reclaim the SAME stale
    'running' row: exactly one must win via FOR UPDATE SKIP LOCKED, the
    other must see no claimable row."""
    op = _make_operation(
        pg_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=50),
        attempt_count=1,
    )
    op_id = op.id

    results: list[int | None] = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def worker() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            claimed = claim_next_background_operation(session)
            with lock:
                results.append(claimed)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(results, key=lambda v: (v is None, v)) == [op_id, None]

    pg_session.query(AdminOperation).filter(AdminOperation.id == op_id).delete()
    pg_session.commit()
