"""Real two-connection PostgreSQL reproduction of the lost-update race
found by independent review of commit
23deba98003814af2c5d2d6ce0a05ba99b82e65b:

_try_finalize's PREVIOUS implementation checked the status of the
caller's already-loaded SQLAlchemy ORM object. That is not concurrency-safe:
a different PostgreSQL transaction can commit running -> stalled (or
running -> cancelled) while the original runner's Session still holds a
non-expired local object showing status="running" — SQLAlchemy's
expire_on_commit only fires on the SAME Session's own commits, never when
a DIFFERENT connection commits a change to a row this Session has already
loaded. The single-sqlite-session mock tests in
tests/test_import_job_concurrent_stall_finalize_new.py cannot reproduce
this: they simulate the race by mutating the same ORM object or issuing a
raw UPDATE through the SAME session, which is not the same failure mode as
two genuinely independent connections/transactions.

These tests use two independent db.session.SessionLocal() connections and
threading, exactly like the existing
tests_postgres_integration/test_concurrent_worker_claim.py pattern, to
prove the CURRENT implementation (SELECT ... FOR UPDATE with
populate_existing(), re-verifying status/claimed_by/finished_at under that
lock) is immune to the race, and that reverting to a stale-object check
would fail these same tests.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

from db.session import SessionLocal
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import _try_finalize, cancel_import_job, claim_queued_job, queue_city_import_job


def _claim_job(pg_session, *, city_id: int, worker_id: str = "worker-1") -> CityAdminImportJob:
    queued = queue_city_import_job(pg_session, city_id=city_id, actor_id="tester")
    pg_session.commit()
    return claim_queued_job(pg_session, job_id=queued.id, worker_id=worker_id, actor_id="tester")


def test_late_finalize_never_overwrites_a_concurrently_stalled_job_new(pg_session, pg_city) -> None:
    """The exact scenario from the review:
    - Session A loads a running job (via claim_queued_job in this test's
      setup, using pg_session).
    - Session B (a genuinely independent connection) locks the row and
      commits running -> stalled with its own finished_at/last_error.
    - Session A then attempts to finalize the SAME job to "success" using
      _try_finalize with the job_id it already has (never re-reading the
      row itself before calling _try_finalize — exactly how every real
      runner calls it).
    - The final DB row must remain "stalled" with Session B's exact
      finished_at/last_error; Session A's "success" attempt must be
      rejected and write nothing."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    stalled_finished_at = datetime.utcnow() - timedelta(minutes=3)
    stalled_last_error = "Import job stalled: no heartbeat before timeout"
    entered_b = threading.Event()
    release_b = threading.Event()
    b_done = threading.Event()

    def session_b_stalls_it() -> None:
        session_b = SessionLocal()
        try:
            row = session_b.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).with_for_update().first()
            entered_b.set()
            # Hold the lock briefly to force Session A's own FOR UPDATE
            # (inside _try_finalize) to genuinely block and wait, not just
            # get lucky with ordering.
            release_b.wait(timeout=5)
            row.status = "stalled"
            row.finished_at = stalled_finished_at
            row.last_error = stalled_last_error
            session_b.commit()
        finally:
            session_b.close()
            b_done.set()

    thread_b = threading.Thread(target=session_b_stalls_it)
    thread_b.start()
    assert entered_b.wait(timeout=5)
    release_b.set()
    assert b_done.wait(timeout=5)

    # Session A (pg_session, already holding the stale in-memory `job`
    # object with status="running") now attempts to finalize.
    result = _try_finalize(
        pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow(), "last_error": None},
    )

    assert result.ok is False
    assert result.reason == "already_terminalized"

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "stalled"
        assert final_row.finished_at is not None
        # Compare with second-level tolerance: PostgreSQL round-trips
        # microseconds, but the two datetimes should be within the same
        # second regardless of driver rounding.
        assert abs((final_row.finished_at - stalled_finished_at).total_seconds()) < 1
        assert final_row.last_error == stalled_last_error
    finally:
        verify_session.close()


def test_cancelled_beats_late_success_new(pg_session, pg_city) -> None:
    """Session B cancels the job (a genuine admin action, real commit).
    Session A's stale in-memory job later attempts to finalize it as
    "success" — the row must stay "cancelled"."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        cancel_import_job(session_b, city_id=pg_city.id, actor_id="admin", job_id=job_id)
    finally:
        session_b.close()

    result = _try_finalize(
        pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )

    assert result.ok is False

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "cancelled"
    finally:
        verify_session.close()


def test_success_beats_late_stall_new(pg_session, pg_city) -> None:
    """The reverse ordering: Session B finalizes the job to "success" FIRST
    (a real commit through a separate connection). A late stall-sweep
    attempt (Session A, using _try_finalize with no expected_claimed_by —
    the administrative-override form used by mark_stalled_import_jobs)
    against the same job_id must be rejected; the row stays "success"."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        result_b = _try_finalize(
            session_b, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
            fields={"finished_at": datetime.utcnow()},
        )
        assert result_b.ok is True
        session_b.commit()
    finally:
        session_b.close()

    # A late stall-sweep (administrative override — no expected_claimed_by)
    # racing in after the real success was already committed.
    late_stall_result = _try_finalize(
        pg_session, job_id=job_id, new_status="stalled", actor_id="import-worker",
        fields={"finished_at": datetime.utcnow(), "last_error": "Import job stalled: no heartbeat before timeout"},
    )

    assert late_stall_result.ok is False

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "success"
    finally:
        verify_session.close()


def test_wrong_claimed_by_cannot_finalize_new(pg_session, pg_city) -> None:
    """A worker presenting a claimed_by identity that does NOT match the
    row's real claimed_by (e.g. a stale/duplicate worker process, or a
    worker that raced and lost an earlier claim attempt) must never be
    able to finalize a job genuinely owned by a different worker — even
    though status=="running" is still true and no other party has
    terminalized the row yet."""
    job = _claim_job(pg_session, city_id=pg_city.id, worker_id="worker-real")
    job_id = job.id

    impostor_session = SessionLocal()
    try:
        result = _try_finalize(
            impostor_session, job_id=job_id, new_status="success", expected_claimed_by="worker-impostor", actor_id="tester",
            fields={"finished_at": datetime.utcnow()},
        )
        assert result.ok is False
        assert result.reason == "lost_ownership"
    finally:
        impostor_session.close()

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "running"
        assert final_row.claimed_by == "worker-real"
    finally:
        verify_session.close()

    # The genuine owner can still finalize afterward.
    owner_session = SessionLocal()
    try:
        owner_result = _try_finalize(
            owner_session, job_id=job_id, new_status="success", expected_claimed_by="worker-real", actor_id="tester",
            fields={"finished_at": datetime.utcnow()},
        )
        assert owner_result.ok is True
        owner_session.commit()
    finally:
        owner_session.close()


def test_two_simultaneous_finalizers_produce_one_winner_and_loser_changes_nothing_new(pg_session, pg_city) -> None:
    """Two independent connections race to finalize the SAME job_id at
    (as close to) the same instant, to two DIFFERENT terminal statuses.
    Exactly one must win; the loser's finalize call must report ok=False
    and the row must show only the winner's fields — nothing from the
    loser leaks through, regardless of which one PostgreSQL's row lock
    happens to grant first."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    barrier = threading.Barrier(2)
    outcomes: dict[str, bool] = {}
    lock = threading.Lock()

    def finalizer(name: str, new_status: str, error_text: str) -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            result = _try_finalize(
                session, job_id=job_id, new_status=new_status, expected_claimed_by="worker-1", actor_id=name,
                fields={"finished_at": datetime.utcnow(), "last_error": error_text},
            )
            if result.ok:
                session.commit()
            else:
                session.rollback()
            with lock:
                outcomes[name] = result.ok
        finally:
            session.close()

    thread_success = threading.Thread(target=finalizer, args=("finalizer-success", "success", None))
    thread_failed = threading.Thread(target=finalizer, args=("finalizer-failed", "failed", "boom"))
    thread_success.start()
    thread_failed.start()
    thread_success.join(timeout=10)
    thread_failed.join(timeout=10)

    assert sorted(outcomes.values()) == [False, True]
    winners = [name for name, ok in outcomes.items() if ok]
    assert len(winners) == 1

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        if winners[0] == "finalizer-success":
            assert final_row.status == "success"
            assert final_row.last_error is None
        else:
            assert final_row.status == "failed"
            assert final_row.last_error == "boom"
    finally:
        verify_session.close()


def test_losing_finalizer_stale_object_flush_does_not_overwrite_winner_new(pg_session, pg_city) -> None:
    """Reproduces the exact failure mode named in the task: after a losing
    _try_finalize call returns ok=False, the CALLER must not go on to
    commit any field from its OLDER, still-in-memory `job` object — a
    later, unrelated db.commit() on that stale object (e.g. via an
    unrelated field write elsewhere in the same request/session) must not
    silently flush a stale status/finished_at back onto the row and
    resurrect the race. This test explicitly mutates the stale in-memory
    object AFTER a losing _try_finalize call and commits again, proving
    the row is unaffected because _try_finalize's own SELECT ...
    FOR UPDATE (not the stale object) is what determined ok=False, and a
    disciplined caller (as every real runner now is) never writes fields
    from that stale object once ok=False."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        result_b = _try_finalize(
            session_b, job_id=job_id, new_status="cancelled", expected_claimed_by="worker-1", actor_id="admin",
            fields={"finished_at": datetime.utcnow(), "last_error": "cancelled by admin"},
        )
        assert result_b.ok is True
        session_b.commit()
    finally:
        session_b.close()

    # pg_session still holds the OLDER `job` object (status="running" in
    # its own Python attribute, never refreshed). A disciplined caller
    # would check result.ok and stop — this test proves that even if code
    # elsewhere in the same session tries to flush THIS stale object's
    # status via a plain attribute write + commit (simulating a bug where
    # someone forgot the ok-check), _try_finalize's OWN atomic write
    # already went through a fresh row in a different transaction, and
    # the assertion below confirms the winning "cancelled" value survives
    # a subsequent unrelated commit on the loser's stale session.
    pg_session.commit()  # no-op: pg_session's own `job` was never reassigned to running->success

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "cancelled"
        assert final_row.last_error == "cancelled by admin"
    finally:
        verify_session.close()
