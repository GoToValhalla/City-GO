"""Fast SQLite-compatible unit tests for the admin_operations bounded
lease/reclaim/fencing mechanism. See tests_postgres_integration/test_admin_
operation_lease_reclaim.py for the real-concurrency PostgreSQL coverage of
the same contract (SQLite cannot reproduce genuine FOR UPDATE SKIP LOCKED
races, and these tests avoid real threading against the shared, rollback-
wrapped fixture session)."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.admin_operation import AdminOperation
from services.admin_background_operation_service import (
    MAX_ATTEMPTS,
    claim_next_background_operation,
    create_background_operation,
    finalize_background_operation,
    renew_lease,
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


def _same_session_factory(db_session):
    """run_background_operation/renew_lease/finalize_background_operation
    each call session_factory().close() internally; patch close to a no-op
    so the shared fixture session survives across multiple such calls
    within one test."""
    db_session.close = lambda: None
    return lambda: db_session


def test_create_background_operation_starts_with_zero_attempts_new(db_session) -> None:
    op = create_background_operation(db_session, operation_type="coverage_gaps_refresh", actor="tester")
    assert op.status == "queued"
    assert op.attempt_count == 0
    assert op.claimed_at is None
    assert op.lease_expires_at is None
    assert op.lease_generation == 0


def test_claim_sets_lease_claimed_at_worker_id_and_generation_new(db_session) -> None:
    op = _make_operation(db_session)
    claimed = claim_next_background_operation(db_session)
    assert claimed == (op.id, 1)
    db_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 1
    assert op.claimed_at is not None
    assert op.lease_expires_at is not None
    assert op.lease_expires_at > op.claimed_at
    assert op.worker_id
    assert op.lease_generation == 1


def test_stale_running_operation_is_reclaimed_with_new_generation_new(db_session) -> None:
    op = _make_operation(
        db_session,
        status="running",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
        lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
        attempt_count=1,
        lease_generation=5,
    )
    reclaimed = claim_next_background_operation(db_session)
    assert reclaimed == (op.id, 6)
    db_session.refresh(op)
    assert op.status == "running"
    assert op.attempt_count == 2
    assert op.lease_generation == 6


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
    claimed = claim_next_background_operation(db_session)
    assert claimed is None
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
    claimed = claim_next_background_operation(db_session)
    assert claimed is None
    db_session.refresh(op)
    assert op.status == "failed"
    assert op.error_message is not None


def test_no_claimable_operation_returns_none_new(db_session) -> None:
    _make_operation(db_session, status="completed")
    assert claim_next_background_operation(db_session) is None


def test_renew_lease_succeeds_for_matching_generation_new(db_session) -> None:
    op = _make_operation(db_session)
    factory = _same_session_factory(db_session)
    claimed = claim_next_background_operation(db_session)
    operation_id, generation = claimed
    before = db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).one().lease_expires_at

    renewed = renew_lease(operation_id, generation, session_factory=factory)
    assert renewed is True
    after = db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).one().lease_expires_at
    assert after >= before


def test_renew_lease_fails_for_stale_generation_new(db_session) -> None:
    """A worker holding an old (already-superseded) generation must never
    be able to extend the lease -- this is the core anti-steal invariant."""
    op = _make_operation(db_session)
    factory = _same_session_factory(db_session)
    claimed = claim_next_background_operation(db_session)
    operation_id, stale_generation = claimed

    # Force the lease to look expired and let a second claim reclaim it,
    # bumping the generation -- simulating another worker taking over.
    db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).update(
        {"lease_expires_at": datetime.utcnow() - timedelta(seconds=1)}
    )
    db_session.commit()
    reclaimed = claim_next_background_operation(db_session)
    assert reclaimed[0] == operation_id
    assert reclaimed[1] != stale_generation

    # The original (now-stale) worker's renewal attempt must fail.
    renewed = renew_lease(operation_id, stale_generation, session_factory=factory)
    assert renewed is False


def test_finalize_fails_for_stale_generation_new(db_session) -> None:
    """A worker whose lease was stolen must never be able to write a
    terminal result over the new owner's row."""
    op = _make_operation(db_session)
    factory = _same_session_factory(db_session)
    claimed = claim_next_background_operation(db_session)
    operation_id, stale_generation = claimed

    db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).update(
        {"lease_expires_at": datetime.utcnow() - timedelta(seconds=1)}
    )
    db_session.commit()
    claim_next_background_operation(db_session)  # a second worker reclaims it

    finalized = finalize_background_operation(
        operation_id, stale_generation, session_factory=factory, status="completed", result={"ok": True}
    )
    assert finalized is False
    reloaded = db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).one()
    assert reloaded.status == "running"
    assert reloaded.result != {"ok": True}


def test_finalize_succeeds_for_matching_generation_new(db_session) -> None:
    op = _make_operation(db_session)
    factory = _same_session_factory(db_session)
    operation_id, generation = claim_next_background_operation(db_session)

    finalized = finalize_background_operation(
        operation_id, generation, session_factory=factory, status="completed", result={"ok": True}
    )
    assert finalized is True
    reloaded = db_session.query(AdminOperation).filter(AdminOperation.id == operation_id).one()
    assert reloaded.status == "completed"
    assert reloaded.result == {"ok": True}


def test_run_background_operation_completes_a_claimed_row_new(db_session, monkeypatch) -> None:
    op = _make_operation(db_session, operation_type="city_readiness_recalculate", city_slug="test-city")
    op_id = op.id

    def _fake_runner(db, operation):
        return {"status": "success"}

    import services.admin_background_operation_service as svc

    monkeypatch.setattr(svc, "_runner_for", lambda op_type: _fake_runner)
    factory = _same_session_factory(db_session)
    run_background_operation(op_id, session_factory=factory, already_claimed=False)
    reloaded = db_session.query(AdminOperation).filter(AdminOperation.id == op_id).one()
    assert reloaded.status == "completed"
    assert reloaded.result == {"status": "success"}


def test_run_background_operation_marks_failed_on_runner_exception_new(engine, monkeypatch) -> None:
    """Uses a real independent sessionmaker bound to the shared test engine
    (not the db_session fixture's single wrapped connection): the runner's
    own session genuinely rolling back on exception must not affect the
    separately-committed finalize write, exactly like production's
    independent connections. The db_session fixture's connection-bound
    Session cannot model this (see the module docstring).

    engine is session-scoped (shared across the whole test run), so any row
    committed here via a real sessionmaker -- including the SystemLog row
    the exception path writes -- MUST be explicitly deleted: unlike
    db_session, there is no automatic rollback to clean it up."""
    from sqlalchemy.orm import sessionmaker

    from models.system_log import SystemLog

    factory = sessionmaker(bind=engine)
    seed = factory()
    op = _make_operation(seed, operation_type="coverage_gaps_refresh")
    op_id = op.id
    seed.close()

    def _failing_runner(db, operation):
        raise ValueError("boom")

    import services.admin_background_operation_service as svc

    monkeypatch.setattr(svc, "_runner_for", lambda op_type: _failing_runner)
    try:
        run_background_operation(op_id, session_factory=factory, already_claimed=False)

        check = factory()
        reloaded = check.query(AdminOperation).filter(AdminOperation.id == op_id).one()
        assert reloaded.status == "failed"
        assert "boom" in (reloaded.error_message or "")
        check.close()
    finally:
        cleanup = factory()
        cleanup.query(AdminOperation).filter(AdminOperation.id == op_id).delete()
        cleanup.query(SystemLog).filter(SystemLog.request_id == str(op_id)).delete()
        cleanup.commit()
        cleanup.close()
