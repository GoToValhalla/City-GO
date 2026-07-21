"""Fast SQLite-compatible unit tests for the admin_operations bounded
lease/reclaim mechanism. See tests_postgres_integration/test_admin_operation_
lease_reclaim.py for the real-concurrency PostgreSQL coverage of the same
contract (SQLite cannot reproduce genuine FOR UPDATE SKIP LOCKED races)."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.admin_operation import AdminOperation
from services.admin_background_operation_service import (
    MAX_ATTEMPTS,
    claim_next_background_operation,
    create_background_operation,
    run_background_operation,
)


def _make_operation(db_session, **overrides) -> AdminOperation:
    defaults = dict(
        operation_type="coverage_gaps_refresh",
        status="queued",
        actor="test-actor",
        city_slug=None,
        place_ids=[],
        result={},
        attempt_count=0,
    )
    defaults.update(overrides)
    op = AdminOperation(**defaults)
    db_session.add(op)
    db_session.commit()
    db_session.refresh(op)
    return op


def test_create_background_operation_starts_with_zero_attempts_new(db_session) -> None:
    op = create_background_operation(db_session, operation_type="coverage_gaps_refresh", actor="tester")
    assert op.status == "queued"
    assert op.attempt_count == 0
    assert op.claimed_at is None
    assert op.lease_expires_at is None


def test_claim_sets_lease_claimed_at_and_worker_id_new(db_session) -> None:
    op = _make_operation(db_session)
    claimed_id = claim_next_background_operation(db_session)
    assert claimed_id == op.id
    db_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1
    assert op.claimed_at is not None
    assert op.lease_expires_at is not None
    assert op.lease_expires_at > op.claimed_at
    assert op.worker_id


def test_stale_running_operation_is_reclaimed_new(db_session) -> None:
    op = _make_operation(
        db_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
        attempt_count=1,
    )
    reclaimed_id = claim_next_background_operation(db_session)
    assert reclaimed_id == op.id
    db_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2


def test_non_stale_running_operation_is_not_reclaimed_new(db_session) -> None:
    # claim_next_background_operation calls db.rollback() on a no-candidate
    # result. tests/conftest.py's db_session binds a Session directly to an
    # explicit Connection (not an Engine) for whole-test rollback-based
    # isolation, so a mid-test rollback() here would also undo this test's
    # own prior commit()s (there is no savepoint boundary between them) —
    # a fixture characteristic, not a defect in the code under test. Assert
    # on the in-memory ORM object's unmodified attributes instead of
    # re-querying the row after the call; the concurrent-safe DB-level
    # behavior is covered against real PostgreSQL in
    # tests_postgres_integration/test_admin_operation_lease_reclaim.py::
    # test_non_stale_running_operation_is_not_reclaimed_new.
    op = _make_operation(
        db_session,
        status="running",
        claimed_at=datetime.utcnow(),
        lease_expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempt_count=1,
    )
    status_before, attempts_before = op.status, op.attempt_count
    claimed_id = claim_next_background_operation(db_session)
    assert claimed_id is None
    assert status_before == "running"
    assert attempts_before == 1


def test_max_attempts_reached_terminalizes_new(db_session) -> None:
    op = _make_operation(
        db_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
        attempt_count=MAX_ATTEMPTS,
    )
    claimed_id = claim_next_background_operation(db_session)
    assert claimed_id is None
    db_session.refresh(op)
    assert op.status == "failed"
    assert op.error_message is not None


def test_no_claimable_operation_returns_none_new(db_session) -> None:
    _make_operation(db_session, status="completed")
    assert claim_next_background_operation(db_session) is None


def test_run_background_operation_completes_a_claimed_row_new(db_session, monkeypatch) -> None:
    op = _make_operation(db_session, operation_type="city_readiness_recalculate", city_slug="test-city")
    op_id = op.id

    def _fake_runner(db, operation):
        return {"status": "success"}

    import services.admin_background_operation_service as svc

    monkeypatch.setattr(svc, "_runner_for", lambda op_type: _fake_runner)
    # run_background_operation closes whatever session its factory returns;
    # keep the shared fixture session alive across the call so later
    # assertions in this test (and fixture teardown) still work.
    monkeypatch.setattr(db_session, "close", lambda: None)
    run_background_operation(op_id, session_factory=lambda: db_session, already_claimed=False)
    reloaded = db_session.query(AdminOperation).filter(AdminOperation.id == op_id).one()
    assert reloaded.status == "completed"
    assert reloaded.result == {"status": "success"}
