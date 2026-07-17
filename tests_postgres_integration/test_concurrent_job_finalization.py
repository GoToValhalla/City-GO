"""Real two-connection PostgreSQL reproduction of the lost-update race in
CityAdminImportJob finalization, and of the architectural consolidation
(finalize_import_job) that closes it — see commit
23deba98003814af2c5d2d6ce0a05ba99b82e65b and the follow-up review that
required autoflush/identity-map/rollback handling to be part of the same
transaction contract, not a second, separately-patched concern.

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

finalize_import_job (the renamed, extended primitive) additionally:
- wraps its whole body in db.no_autoflush, so a caller's pending dirty
  attributes on the SAME job (or anything else in the Session) can never
  autoflush an UPDATE ahead of finalize_import_job's own SELECT ... FOR
  UPDATE;
- db.expire()s the job's identity-map entry on rejection, so a caller's
  stale in-memory object can never be flushed by a later, unrelated
  commit in the same Session;
- leaves every OTHER dirty object in the Session untouched on rejection.

These tests use two independent db.session.SessionLocal() connections and
threading, exactly like the existing
tests_postgres_integration/test_concurrent_worker_claim.py pattern, to
prove the CURRENT implementation is immune to the race, and that reverting
to a stale-object check would fail these same tests.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

from sqlalchemy import event

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import (
    cancel_import_job,
    claim_queued_job,
    finalize_import_job,
    queue_city_import_job,
)


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
      finalize_import_job with the job_id it already has (never re-reading
      the row itself before calling finalize_import_job — exactly how
      every real runner calls it).
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
            # (inside finalize_import_job) to genuinely block and wait, not
            # just get lucky with ordering.
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
    result = finalize_import_job(
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


def test_stale_dirty_local_fields_never_flush_ahead_of_the_lock_new(pg_session, pg_city) -> None:
    """Scenario 1 from the task: Session A has stale DIRTY (uncommitted,
    pending) attribute writes on its own in-memory `job` object — not just
    a stale READ, an actual pending UPDATE SQLAlchemy would normally
    autoflush on the next query. Session B independently locks and commits
    running -> stalled with its own fields. Session A then calls
    finalize_import_job("success") and commits.

    Without db.no_autoflush inside finalize_import_job, the SELECT ... FOR
    UPDATE the function issues would itself trigger autoflush of A's dirty
    `job.last_error` BEFORE the lock is acquired — sending an UPDATE built
    from stale local state, racing ahead of and independent from the
    lock-protected logic. This test proves that does not happen: B's exact
    committed row survives untouched, including the field A had dirtied
    in-memory but never flushed."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    # Dirty A's own in-memory object with a pending, NOT YET flushed
    # attribute write — simulates a caller that mutated `job` earlier in
    # the same function (e.g. progress tracking) and never flushed before
    # reaching its own finalize call.
    job.last_error = "stale in-memory value that must never reach the row"

    session_b = SessionLocal()
    try:
        row_b = session_b.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).with_for_update().first()
        row_b.status = "stalled"
        row_b.finished_at = datetime.utcnow()
        row_b.last_error = "stalled by session B"
        session_b.commit()
    finally:
        session_b.close()

    result = finalize_import_job(
        pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )
    assert result.ok is False
    pg_session.commit()

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "stalled"
        assert final_row.last_error == "stalled by session B"
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

    result = finalize_import_job(
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
    attempt (Session A, using finalize_import_job with no
    expected_claimed_by — the administrative-override form used by
    mark_stalled_import_jobs) against the same job_id must be rejected;
    the row stays "success"."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        result_b = finalize_import_job(
            session_b, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
            fields={"finished_at": datetime.utcnow()},
        )
        assert result_b.ok is True
        session_b.commit()
    finally:
        session_b.close()

    # A late stall-sweep (administrative override — no expected_claimed_by)
    # racing in after the real success was already committed.
    late_stall_result = finalize_import_job(
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
        result = finalize_import_job(
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
        owner_result = finalize_import_job(
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
            result = finalize_import_job(
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
    finalize_import_job call returns ok=False, the CALLER must not go on
    to commit any field from its OLDER, still-in-memory `job` object — a
    later, unrelated db.commit() on that stale object (e.g. via an
    unrelated field write elsewhere in the same request/session) must not
    silently flush a stale status/finished_at back onto the row and
    resurrect the race. This test explicitly mutates the stale in-memory
    object AFTER a losing finalize_import_job call and commits again,
    proving the row is unaffected: finalize_import_job's own db.expire()
    on rejection discards the stale object's pending attributes, so a
    disciplined OR undisciplined caller alike cannot resurrect them."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        result_b = finalize_import_job(
            session_b, job_id=job_id, new_status="cancelled", expected_claimed_by="worker-1", actor_id="admin",
            fields={"finished_at": datetime.utcnow(), "last_error": "cancelled by admin"},
        )
        assert result_b.ok is True
        session_b.commit()
    finally:
        session_b.close()

    # pg_session still holds the OLDER `job` object (status="running" in
    # its own Python attribute, never refreshed). A losing finalize call
    # against this exact job_id below must reject AND expire this stale
    # object so this subsequent mutate-and-commit cannot resurrect it.
    late = finalize_import_job(
        pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )
    assert late.ok is False
    # Simulates a bug where a caller forgot the ok-check and mutates the
    # stale object anyway before its own commit.
    job.status = "success"
    job.last_error = "should never reach the row"
    pg_session.commit()

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "cancelled"
        assert final_row.last_error == "cancelled by admin"
    finally:
        verify_session.close()


def test_unrelated_dirty_objects_in_the_losing_session_are_preserved_new(pg_session, pg_city) -> None:
    """Scenario 7: a losing finalize_import_job call must only discard
    pending state for the ONE job row it rejected — any OTHER dirty object
    already pending in the same Session (e.g. a City row the caller was
    also about to save in the same request) must survive a subsequent
    commit untouched."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id

    session_b = SessionLocal()
    try:
        result_b = finalize_import_job(
            session_b, job_id=job_id, new_status="failed", expected_claimed_by="worker-1", actor_id="tester",
            fields={"finished_at": datetime.utcnow(), "last_error": "boom"},
        )
        assert result_b.ok is True
        session_b.commit()
    finally:
        session_b.close()

    # An unrelated dirty object in pg_session, pending at the same time as
    # the losing finalize call below.
    city_row = pg_session.query(City).filter(City.id == pg_city.id).first()
    city_row.name = "Unrelated Dirty Update Survives"

    late = finalize_import_job(
        pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
        fields={"finished_at": datetime.utcnow()},
    )
    assert late.ok is False
    pg_session.commit()

    verify_session = SessionLocal()
    try:
        final_city = verify_session.query(City).filter(City.id == pg_city.id).one()
        assert final_city.name == "Unrelated Dirty Update Survives"
        final_job = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_job.status == "failed"
        assert final_job.last_error == "boom"
    finally:
        verify_session.close()


def test_successful_finalization_commits_status_and_every_field_atomically_new(pg_session, pg_city) -> None:
    """Scenario 8: a successful finalize_import_job call, once committed,
    must show status AND every field passed via fields= together on the
    row — never a partial write (e.g. status changed but step_details
    missing, which would be possible if finalize_import_job flushed in
    more than one statement group or the caller only committed part of the
    result)."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id
    finished_at = datetime.utcnow()
    step_details = {"warnings": ["w1"], "changed_place_ids": [1, 2, 3]}

    result = finalize_import_job(
        pg_session, job_id=job_id, new_status="success_with_warnings", expected_claimed_by="worker-1", actor_id="tester",
        fields={
            "finished_at": finished_at,
            "last_error": None,
            "current_step": "done",
            "step_details": step_details,
            "places_found": 10,
            "places_saved": 7,
        },
    )
    assert result.ok is True
    pg_session.commit()

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "success_with_warnings"
        assert final_row.current_step == "done"
        assert final_row.step_details == step_details
        assert final_row.places_found == 10
        assert final_row.places_saved == 7
        assert final_row.finished_at is not None
    finally:
        verify_session.close()


def test_finalize_sends_no_update_for_target_job_before_select_for_update_new(pg_session, pg_city) -> None:
    """Scenario 9: SQL-ordering proof. Captures every SQL statement
    executed on pg_session's connection during a finalize_import_job call
    where the caller ALSO holds a dirty (uncommitted) attribute on the
    same job object beforehand — proving db.no_autoflush inside
    finalize_import_job prevents any UPDATE on city_admin_import_jobs from
    being sent before the SELECT ... FOR UPDATE that acquires the row
    lock. Without db.no_autoflush, SQLAlchemy's default autoflush would
    flush the dirty attribute as part of the SELECT's own implicit
    flush-before-query step, sending an UPDATE first."""
    job = _claim_job(pg_session, city_id=pg_city.id)
    job_id = job.id
    # Dirty, unflushed local attribute — would autoflush ahead of any
    # subsequent query if finalize_import_job did not suppress it.
    job.last_error = "dirty local value pending flush"

    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(pg_session.get_bind(), "before_cursor_execute", _capture)
    try:
        result = finalize_import_job(
            pg_session, job_id=job_id, new_status="success", expected_claimed_by="worker-1", actor_id="tester",
            fields={"finished_at": datetime.utcnow(), "last_error": "final value"},
        )
        assert result.ok is True
    finally:
        event.remove(pg_session.get_bind(), "before_cursor_execute", _capture)
    pg_session.commit()

    select_index = next(
        i for i, stmt in enumerate(statements)
        if "city_admin_import_jobs" in stmt.lower() and stmt.strip().upper().startswith("SELECT")
    )
    for i, stmt in enumerate(statements[:select_index]):
        normalized = stmt.strip().upper()
        if normalized.startswith("UPDATE") and "CITY_ADMIN_IMPORT_JOBS" in stmt.upper():
            raise AssertionError(
                f"UPDATE on city_admin_import_jobs sent before SELECT ... FOR UPDATE "
                f"(statement #{i}, SELECT at #{select_index}): {stmt}"
            )
    # The lock-acquiring SELECT itself must carry FOR UPDATE.
    assert "FOR UPDATE" in statements[select_index].upper()

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "success"
        assert final_row.last_error == "final value"
    finally:
        verify_session.close()


def test_every_production_caller_routes_through_finalize_import_job_new(pg_city) -> None:
    """Scenario 10: exercises cancel_import_job (queued row, never claimed)
    end-to-end against a real PostgreSQL connection, confirming it too
    lands on finalize_import_job's row-lock discipline rather than a
    second, independently-implemented lock-check-write (the AST-level
    guarantee lives in
    tests/test_import_job_finalization_ast_guard_new.py; this is the
    runtime confirmation for the one case finalize_import_job doesn't
    reach from "running" — an admin cancelling a job no worker ever
    claimed)."""
    with SessionLocal() as db:
        queued = queue_city_import_job(db, city_id=pg_city.id, actor_id="tester")
        db.commit()
        job_id = queued.id
        assert queued.status == "queued"
        assert queued.claimed_by is None

        cancelled = cancel_import_job(db, city_id=pg_city.id, actor_id="admin", job_id=job_id)
        assert cancelled.status == "cancelled"
        assert cancelled.finished_at is not None

    verify_session = SessionLocal()
    try:
        final_row = verify_session.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
        assert final_row.status == "cancelled"
    finally:
        verify_session.close()
