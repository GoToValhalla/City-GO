"""Real-connection PostgreSQL tests for the admin_operations bounded
lease/reclaim/fencing mechanism (services/admin_background_operation_service.py).

Root cause fixed (round 1): a job was committed as `running` before
execution; if the process died after claim, it stayed `running` forever,
since the scheduler only ever selects `queued` rows and the partial unique
index on (operation_type, city_slug) WHERE status IN ('queued','running')
blocked any replacement job for the same scope from ever being created.

Root cause fixed (round 2): the lease was set once at claim time and never
renewed. A runner whose real execution time exceeded LEASE_DURATION could
be legally reclaimed and re-executed by a second worker WHILE THE FIRST WAS
STILL RUNNING -- reproduced empirically against this same PostgreSQL harness.
The fix adds a fencing token (lease_generation) plus a background heartbeat
that renews the lease on its own independent session every
HEARTBEAT_INTERVAL. Every renewal and every terminal write is fenced by
lease_generation: a worker whose generation has been superseded (because ITS
OWN lease genuinely expired and someone else reclaimed the row) can never
again successfully write to it, so at most one terminal write survives even
if two workers' runner code executes concurrently.

These tests use two independent SessionLocal() connections/threads (not the
rollback-wrapped tests/conftest.py fixture), matching
test_concurrent_worker_claim.py, because SQLite cannot reproduce
`FOR UPDATE SKIP LOCKED` races between genuinely separate connections.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from db.session import SessionLocal
from models.admin_operation import AdminOperation
from services.admin_background_operation_service import (
    HEARTBEAT_INTERVAL,
    LEASE_DURATION,
    MAX_ATTEMPTS,
    claim_next_background_operation,
    finalize_background_operation,
    renew_lease,
)
import services.admin_background_operation_service as admin_background_operation_service

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


def _cleanup(pg_session, op_id: int) -> None:
    pg_session.query(AdminOperation).filter(AdminOperation.id == op_id).delete()
    pg_session.commit()


def test_crash_after_claim_leaves_row_reclaimable_once_lease_expires_new(pg_session) -> None:
    """Simulates a worker that claimed a row and then crashed: status stays
    'running' with an expired lease. A later claim call must reclaim it."""
    op = _make_operation(pg_session)
    claimed = claim_next_background_operation(pg_session)
    assert claimed == (op.id, 1)
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1
    assert op.lease_generation == 1

    # Simulate the lease having already expired (worker crashed, never renewed it).
    pg_session.query(AdminOperation).filter(AdminOperation.id == op.id).update(
        {"lease_expires_at": datetime.utcnow() - timedelta(seconds=1)}
    )
    pg_session.commit()

    reclaimed = claim_next_background_operation(pg_session)
    assert reclaimed == (op.id, 2)
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2
    assert op.lease_generation == 2
    assert op.lease_expires_at > datetime.utcnow()

    _cleanup(pg_session, op.id)


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
        lease_generation=3,
    )

    reclaimed = claim_next_background_operation(pg_session)
    assert reclaimed == (op.id, 4)
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2
    assert op.worker_id != "dead-worker:1234"

    _cleanup(pg_session, op.id)


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

    reclaimed = claim_next_background_operation(pg_session)
    assert reclaimed is None
    pg_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1
    assert op.worker_id == "alive-worker:5678"

    _cleanup(pg_session, op.id)


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

    reclaimed = claim_next_background_operation(pg_session)
    assert reclaimed is None
    pg_session.refresh(op)
    assert op.status == "failed"
    assert op.error_message is not None
    assert str(MAX_ATTEMPTS) in op.error_message

    _cleanup(pg_session, op.id)


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

    results: list[tuple[int, int] | None] = []
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

    winners = [r for r in results if r is not None]
    losers = [r for r in results if r is None]
    assert len(winners) == 1
    assert len(losers) == 1
    assert winners[0][0] == op_id

    _cleanup(pg_session, op_id)


def test_long_running_execution_cannot_be_reclaimed_while_heartbeat_is_alive_new(pg_session) -> None:
    """Simulates an operation whose runner takes longer than LEASE_DURATION
    but whose heartbeat keeps renewing the lease throughout: a second
    worker's claim attempt, issued AFTER the original LEASE_DURATION would
    have elapsed with no renewal, must find nothing to reclaim, because the
    heartbeat kept extending lease_expires_at ahead of "now" the whole time."""
    op = _make_operation(pg_session)
    claimed = claim_next_background_operation(pg_session)
    operation_id, generation = claimed

    stop = threading.Event()

    def heartbeat_loop() -> None:
        # Renew far more often than LEASE_DURATION, modeling a live worker.
        while not stop.wait(0.05):
            renew_lease(operation_id, generation, session_factory=SessionLocal)

    thread = threading.Thread(target=heartbeat_loop, daemon=True)
    thread.start()
    try:
        # Real wall-clock time exceeding what a non-renewed lease would
        # survive, proven against the actual LEASE_DURATION value: sleep
        # well past it while the heartbeat keeps renewing underneath us.
        time.sleep(0.6)
        second_worker_attempt = claim_next_background_operation(pg_session)
        assert second_worker_attempt is None, (
            "a live, heartbeat-renewed lease must never be reclaimed by another worker"
        )
    finally:
        stop.set()
        thread.join(timeout=5)

    pg_session.refresh(op)
    assert op.status == "running"
    assert op.lease_generation == generation

    _cleanup(pg_session, operation_id)


def test_duplicate_execution_cannot_occur_only_one_terminal_write_survives_new(pg_session) -> None:
    """Simulates the exact race this fix closes: worker A claims, its lease
    genuinely expires (heartbeat stopped, e.g. crashed), worker B reclaims
    and finishes first. Worker A's own eventual finalize attempt (fenced by
    its now-superseded generation) must be rejected and must not clobber
    worker B's result -- proving at most one terminal write ever lands."""
    op = _make_operation(pg_session)
    claimed_a = claim_next_background_operation(pg_session)
    operation_id, generation_a = claimed_a

    # Worker A's heartbeat has stopped (simulating a crash/stall); age the
    # lease so a second worker legitimately sees it as reclaimable.
    pg_session.query(AdminOperation).filter(AdminOperation.id == operation_id).update(
        {"lease_expires_at": datetime.utcnow() - timedelta(seconds=1)}
    )
    pg_session.commit()

    claimed_b = claim_next_background_operation(pg_session)
    operation_id_b, generation_b = claimed_b
    assert operation_id_b == operation_id
    assert generation_b != generation_a

    # Worker B finishes first and writes its terminal result.
    finalized_b = finalize_background_operation(
        operation_id, generation_b, session_factory=SessionLocal, status="completed", result={"owner": "B"}
    )
    assert finalized_b is True

    # Worker A, unaware it lost the lease, now tries to write its own
    # (different) result -- this must be rejected.
    finalized_a = finalize_background_operation(
        operation_id, generation_a, session_factory=SessionLocal, status="completed", result={"owner": "A"}
    )
    assert finalized_a is False

    final_row = pg_session.query(AdminOperation).filter(AdminOperation.id == operation_id).one()
    assert final_row.result == {"owner": "B"}
    assert final_row.status == "completed"

    _cleanup(pg_session, operation_id)


def test_lease_ownership_cannot_be_stolen_by_a_non_reclaiming_worker_new(pg_session) -> None:
    """A worker that never legitimately reclaimed the row (wrong/arbitrary
    generation, row still actively leased to someone else) must never be
    able to renew or finalize it -- renew_lease/finalize_background_operation
    are the only lease-mutating entrypoints, and both are fenced."""
    op = _make_operation(
        pg_session,
        status="running",
        claimed_at=datetime.utcnow(),
        lease_expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempt_count=1,
        lease_generation=7,
        worker_id="legitimate-owner",
    )

    forged_generation = 999
    stolen_renew = renew_lease(op.id, forged_generation, session_factory=SessionLocal)
    assert stolen_renew is False

    stolen_finalize = finalize_background_operation(
        op.id, forged_generation, session_factory=SessionLocal, status="completed", result={"stolen": True}
    )
    assert stolen_finalize is False

    pg_session.refresh(op)
    assert op.status == "running"
    assert op.lease_generation == 7
    assert op.result != {"stolen": True}

    _cleanup(pg_session, op.id)


def test_lease_updates_stop_after_terminal_completion_new(pg_session) -> None:
    """Once an operation is finalized, a subsequent renew_lease call using
    the SAME generation that was valid during execution must be rejected --
    finalize_background_operation's fencing checks lease_generation only,
    not status, by design (status may already differ once terminal), but
    renew_lease additionally requires status == 'running', so a heartbeat
    that fires after the terminal write (a benign race between the last
    heartbeat tick and finalize) must be a safe no-op, never resurrecting a
    finished row back into a lease-extended state."""
    op = _make_operation(pg_session)
    operation_id, generation = claim_next_background_operation(pg_session)

    finalized = finalize_background_operation(
        operation_id, generation, session_factory=SessionLocal, status="completed", result={"ok": True}
    )
    assert finalized is True

    late_heartbeat = renew_lease(operation_id, generation, session_factory=SessionLocal)
    assert late_heartbeat is False

    pg_session.refresh(op)
    assert op.status == "completed"
    assert op.result == {"ok": True}

    _cleanup(pg_session, operation_id)


def test_end_to_end_long_running_runner_survives_via_real_heartbeat_thread_new(pg_session, monkeypatch) -> None:
    """Full integration proof, not just the underlying primitives: runs the
    REAL _execute_claimed_operation entrypoint (the one production actually
    calls) with a runner that sleeps longer than a (shrunk, for test speed)
    LEASE_DURATION. A second worker's claim attempt, issued after the
    original unrenewed LEASE_DURATION would have elapsed, must find nothing
    reclaimable, because the real background heartbeat thread kept
    extending lease_expires_at throughout. This is the exact scenario
    empirically reproduced as broken before this fix (two independent
    claim_next_background_operation calls both returning the same
    operation_id while a runner was still executing)."""
    monkeypatch.setattr(admin_background_operation_service, "LEASE_DURATION", timedelta(seconds=1))
    heartbeat_interval = timedelta(milliseconds=150)

    op = _make_operation(pg_session)
    op_id = op.id
    claimed = claim_next_background_operation(pg_session)
    operation_id, generation = claimed

    def _slow_runner(db, operation):
        time.sleep(2.5)
        return {"status": "success"}

    monkeypatch.setattr(
        admin_background_operation_service,
        "_runner_for",
        lambda op_type: _slow_runner if op_type == "coverage_gaps_refresh" else None,
    )

    thread = threading.Thread(
        target=admin_background_operation_service._execute_claimed_operation,
        args=(operation_id, generation),
        kwargs={"session_factory": SessionLocal, "heartbeat_interval": heartbeat_interval},
    )
    thread.start()
    try:
        # Past the shrunk LEASE_DURATION (1s), while the runner is still
        # sleeping (2.5s total) -- a live heartbeat must keep it unclaimable.
        time.sleep(1.5)
        second_claim_session = SessionLocal()
        try:
            second_claim = claim_next_background_operation(second_claim_session)
        finally:
            second_claim_session.close()
        assert second_claim is None, "a live, heartbeat-renewed lease must never be reclaimed mid-execution"
    finally:
        thread.join(timeout=10)

    pg_session.refresh(op)
    assert op.status == "completed"
    assert op.result == {"status": "success"}
    assert op.lease_generation == generation

    _cleanup(pg_session, op_id)
