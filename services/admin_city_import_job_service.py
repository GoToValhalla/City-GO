"""Очередь и выполнение admin city import jobs."""
from __future__ import annotations

import inspect
from datetime import datetime

from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_job_payload import SNAPSHOT_KEY
from services.admin_city_import_log import log_import_event
from services.admin_import_job_change_service import CHANGE_TYPES, record_place_changes
from services.city_readiness.score import compute_city_readiness
from services.import_publication_finalize import finalize_import_publication
from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
from services.import_pipeline.runner import run_enrichment_pipeline
from services.import_pipeline.steps import STEP_CANCELLED, STEP_ERROR, STEP_QUEUED
from services.import_pipeline_foundation import run_foundation_pipeline
from services.photo_enrichment_diagnostics import attach_photo_diagnostics_to_summary, build_photo_enrichment_diagnostics
from services.place_auto_repair_service import PlaceAutoRepairService

class DuplicateActiveJobError(ValueError):
    """Raised when a queue action is attempted while a job is already
    queued/running for the city — prevents duplicate active jobs from
    repeated admin clicks (e.g. double-clicking "Добрать фото")."""

    def __init__(self, *, city_id: int, job_id: int, job_status: str, source: str):
        self.city_id = city_id
        self.job_id = job_id
        self.job_status = job_status
        self.source = source
        super().__init__("Pipeline уже выполняется")


SOURCE_FULL_IMPORT = "admin_city_import"
SOURCE_ENRICHMENT_ONLY = "admin_city_enrichment"
SOURCE_SNAPSHOT_REFRESH = "admin_snapshot_refresh"
SOURCE_ADDRESS_ENRICHMENT = "admin_address_enrichment"
SOURCE_PHOTO_ENRICHMENT = "admin_photo_enrichment"
ADDRESS_LIMIT = 5000
IMAGE_LIMIT = 2000
AUTO_REPAIR_CITY_SCAN_LIMIT = 1000

# Severity order (least to most severe) for combining the terminal status of
# independent pipeline stages (legacy collection/enrichment + foundation
# source-enrichment) into one truthful job status. A stage's status must
# never be silently widened back to "success" once any stage reported a
# worse outcome.
_STATUS_SEVERITY = {
    "success": 0,
    "success_with_warnings": 1,
    "partial_success": 2,
    "failed": 3,
}


def _combine_status(*statuses: str) -> str:
    """Return the most severe of the given terminal statuses.

    Unknown/blank statuses are treated as "success" so a stage that didn't
    report anything doesn't spuriously downgrade the combined result.
    """

    worst = "success"
    worst_rank = 0
    for status in statuses:
        rank = _STATUS_SEVERITY.get(status, 0)
        if rank > worst_rank:
            worst = status
            worst_rank = rank
    return worst


# --- Immutable lifecycle: explicit allowed-transition map -------------------
#
# queued -> running
# running -> success | success_with_warnings | partial_success | failed
# running -> stalled  (recovery marks a stuck row terminal; see
#                       mark_stalled_import_jobs in admin_city_import_tasks.py)
# queued  -> cancelled (an admin cancels before a worker ever claims it)
# running -> cancelled (an admin cancels a running job)
#
# Every other row->status transition is invalid and fails closed: no
# terminal status (success/success_with_warnings/partial_success/failed/
# cancelled/stalled) may ever transition to queued or running. A retry
# never mutates a terminal row's status — it inserts a brand-new row
# instead (see enqueue_or_retry_job below).
TERMINAL_STATUSES = frozenset({"success", "success_with_warnings", "partial_success", "failed", "cancelled", "stalled"})
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    # "failed" here covers a worker claiming a job and then crashing before
    # its own runner function reaches its first `running` transition (e.g.
    # an exception raised by _resolve_run_job itself) — the row is claimed
    # but never actually started, so it must still be terminable directly
    # from queued rather than getting stuck queued forever.
    "queued": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"success", "success_with_warnings", "partial_success", "failed", "stalled", "cancelled"}),
}

# Distinguishes "caller passed expected_claimed_by=None because it wants to
# require an unclaimed row" (not applicable here, claimed_by is never None
# on a running row) from "caller passed no expected_claimed_by argument at
# all, meaning ownership is not checked" — used by finalize_import_job.
_UNSET = object()

# Starting statuses finalize_import_job accepts, per requested terminal
# transition. "running" covers every normal worker/runner completion and
# every recovery sweep (stall, admin mark-stalled). "queued" exists only so
# cancel can terminalize a row a worker never claimed (started_at/claimed_by
# still NULL) through the SAME lock-check-write primitive as every other
# terminal write, instead of a second, separately-maintained code path.
_FINALIZE_FROM_STATUSES: dict[str, frozenset[str]] = {
    "running": frozenset({"success", "success_with_warnings", "partial_success", "failed", "stalled", "cancelled"}),
    "queued": frozenset({"cancelled", "failed"}),
}


class InvalidJobTransitionError(ValueError):
    """Raised when code attempts to move a CityAdminImportJob row through a
    transition not present in _ALLOWED_TRANSITIONS — most importantly, any
    terminal -> queued/running transition, which is exactly the production
    Job #1 corruption (a finished row silently reset back to queued and
    reused by a later, unrelated worker run)."""

    def __init__(self, *, job_id: int, from_status: str, to_status: str):
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"job #{job_id}: invalid transition {from_status} -> {to_status}")


def _transition(db: Session, job: CityAdminImportJob, new_status: str, *, actor_id: str | None = None) -> None:
    """The single place every status write on an existing row must go
    through. Fails closed (raises, does not silently coerce) on any
    transition not explicitly allowed, and records a diagnostic
    system_log event for the rejected attempt so an invalid transition is
    never silently swallowed."""
    old_status = str(job.status)
    if old_status == new_status:
        return
    allowed = _ALLOWED_TRANSITIONS.get(old_status, frozenset())
    if new_status not in allowed:
        log_import_event(
            db, event="import_job_invalid_transition", city_slug=None, actor_id=actor_id, level="error",
            message=f"Rejected invalid transition for job #{job.id}: {old_status} -> {new_status}",
            details={"job_id": job.id, "from_status": old_status, "to_status": new_status}, job_id=job.id,
        )
        raise InvalidJobTransitionError(job_id=job.id, from_status=old_status, to_status=new_status)
    job.status = new_status
    job.updated_at = datetime.utcnow()


class FinalizeResult:
    """Outcome of finalize_import_job. `job` is only meaningful when `ok` is
    True — it is the freshly locked-and-reloaded row, never the caller's
    older in-memory instance. Callers must discard whatever ORM object they
    held before calling finalize_import_job and use `result.job` for every
    subsequent field write; the old object may be reflecting a status this
    transaction never actually observed under lock."""

    __slots__ = ("ok", "job", "reason")

    def __init__(self, *, ok: bool, job: CityAdminImportJob | None, reason: str | None = None):
        self.ok = ok
        self.job = job
        self.reason = reason

    def __bool__(self) -> bool:
        return self.ok


def finalize_import_job(
    db: Session,
    *,
    job_id: int,
    new_status: str,
    expected_claimed_by: str | None = _UNSET,  # type: ignore[assignment]
    actor_id: str | None = None,
    fields: dict[str, object] | None = None,
) -> FinalizeResult:
    """The ONE atomic, database-authoritative terminal-finalization
    primitive for CityAdminImportJob. This is the ONLY function in the
    codebase allowed to write status/finished_at/last_error/current_step/
    step_details/counters onto a job as a terminal write — every runner,
    the worker loop's exception handler, the automatic stall sweep, the
    manual admin mark-stalled endpoint, and cancel all route their terminal
    writes through this single function, so lock discipline, staleness
    handling, and ownership rules cannot drift apart between call sites
    again (see git history: status-only checks, then row locks, then
    stale-refresh, each patched in isolation, never as one contract).

    Never trusts a caller's already-loaded ORM object: that object can be
    reflecting a status this transaction/connection never actually
    observed under lock — a commit made by a DIFFERENT PostgreSQL
    transaction does not expire or refresh objects already attached to
    this Session (expire_on_commit only fires on THIS Session's own
    commits). Two independent Sessions racing to finalize the same job_id
    is exactly the scenario this guards against; see
    tests_postgres_integration/test_concurrent_job_finalization.py for the
    real two-connection reproduction.

    Sequence, all inside one uninterrupted transaction:
    0. db.no_autoflush for the whole body. Without this, the SELECT ... FOR
       UPDATE below would itself trigger SQLAlchemy's autoflush of any
       pending change on this job (or any other dirty object in the same
       Session) BEFORE the lock is acquired — sending an UPDATE built from
       whatever stale local attributes the caller happened to be holding,
       ahead of and independent from the lock-protected read/write this
       function performs. That defeats the entire point of the lock: the
       row would already carry stale data by the time it's re-selected.
    1. SELECT ... FOR UPDATE by job_id (with populate_existing() so even an
       object already in this Session's identity map is overwritten with
       the row's current, lock-protected DB state — never served stale
       from the session cache).
    2. While still holding that lock, verify:
       - status is a valid starting status for new_status (see
         _FINALIZE_FROM_STATUSES — "running" for normal completion/
         recovery, "queued" additionally allowed only for cancelling a
         job no worker ever claimed);
       - claimed_by == expected_claimed_by, UNLESS the caller passed no
         expected_claimed_by at all (the sentinel default), which means
         "administrative action, intentionally overriding whoever holds
         it" (mark_stalled_import_jobs, cancel_import_job, the manual
         admin mark-stalled endpoint);
       - finished_at IS NULL (a row that already has a finished_at was
         terminalized by someone else, even if a bug elsewhere left
         status somehow still "running" — never trust status alone).
    3. If any check fails:
       - write NOTHING to the row (not even a partial field);
       - if the job_id happens to already be present in this Session's
         identity map (e.g. the caller's own stale `job` object from
         before this call), db.expire() it — this discards every pending
         Python-side attribute change on THAT object, so a later, unrelated
         db.commit() in the same Session can never flush a stale
         status/finished_at/last_error the caller never meant to persist
         (the exact failure mode named "stale ORM object reused after
         finalization"). Only this one job's identity-map entry is
         touched — every OTHER dirty object in the Session (unrelated
         cities, places, log rows the caller is also about to commit) is
         left completely untouched, so a losing finalize never forces the
         caller to lose unrelated legitimate work.
       - log a diagnostic event, return FinalizeResult(ok=False, job=None,
         reason=...). The lock itself is released by the caller's own
         commit/rollback exactly as before — this function never commits
         or rolls back itself, so it composes with the caller's existing
         transaction/SAVEPOINT structure.
    4. If all checks pass: apply `_transition` (status + updated_at) and
       every key/value in `fields` onto the freshly loaded row in the SAME
       Python statement block, then db.flush() so the UPDATE is sent to
       PostgreSQL (and would surface any constraint violation) while the
       lock is still held, before returning. Returns
       FinalizeResult(ok=True, job=<freshly loaded row>) — the caller must
       use `result.job`, not its own older object, for anything further.
       The caller still owns commit(); this function only flushes.

    Called with expected_claimed_by=<worker/run identity> from a normal
    runner's own finalization (it must prove it still owns the row);
    called with no expected_claimed_by (administrative override) from
    mark_stalled_import_jobs/cancel_import_job/mark_stuck_import_jobs."""
    with db.no_autoflush:
        job = (
            db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.id == job_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if job is None:
            return FinalizeResult(ok=False, job=None, reason="job_not_found")
        current_status = str(job.status)
        allowed_targets = _FINALIZE_FROM_STATUSES.get(current_status, frozenset())
        ownership_checked = expected_claimed_by is not _UNSET
        ownership_ok = not ownership_checked or job.claimed_by == expected_claimed_by
        status_ok = new_status in allowed_targets and job.finished_at is None
        if not status_ok or not ownership_ok:
            reason = "already_terminalized" if not status_ok else "lost_ownership"
            log_import_event(
                db, event="import_job_finalize_skipped_recovered_externally", city_slug=None, actor_id=actor_id, level="warning",
                message=(
                    f"Job #{job.id} finalize to {new_status} skipped ({reason}): "
                    f"db status={current_status!r} finished_at={job.finished_at!r} claimed_by={job.claimed_by!r} "
                    f"(this run expected claimed_by={expected_claimed_by!r})"
                ),
                details={
                    "job_id": job.id, "attempted_status": new_status, "actual_status": current_status,
                    "actual_finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    "actual_claimed_by": job.claimed_by, "expected_claimed_by": None if not ownership_checked else expected_claimed_by,
                    "reason": reason,
                },
                job_id=job.id,
            )
            # Detach this exact row's identity-map entry from the Session
            # entirely (db.expunge, not db.expire): expiring alone only
            # discards attribute state that was ALREADY pending at the
            # moment of rejection — it does not stop a caller from writing
            # to the (now-expired-but-still-attached) object again
            # afterward, which SQLAlchemy would then autoflush/commit like
            # any other dirty object. expunge makes every future attribute
            # write on this object inert: an expunged instance is no
            # longer session-managed, so nothing it does can ever reach
            # the database through THIS Session again, no matter what a
            # caller does to it after seeing ok=False. This is what makes
            # "a later caller commit cannot flush stale target values" true
            # unconditionally, not just for writes that predate this call.
            if job in db:
                db.expunge(job)
            return FinalizeResult(ok=False, job=None, reason=reason)
        # _transition itself raises InvalidJobTransitionError for anything
        # not in _ALLOWED_TRANSITIONS — a second, independent guard on top
        # of the _FINALIZE_FROM_STATUSES check above (e.g. this catches a
        # caller bug requesting a transition never valid for "running" at
        # all, not just one lost to a race).
        _transition(db, job, new_status, actor_id=actor_id)
        for key, value in (fields or {}).items():
            setattr(job, key, value)
        db.flush()
        return FinalizeResult(ok=True, job=job)


def queue_city_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def queue_city_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    return queue_city_import_job(db, city_id=city_id, actor_id=actor_id)


def queue_city_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_SNAPSHOT_REFRESH, actor_id=actor_id)


def queue_city_address_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_ADDRESS_ENRICHMENT, actor_id=actor_id)


def queue_city_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_PHOTO_ENRICHMENT, actor_id=actor_id)


def load_job_for_run(db: Session, *, job_id: int, city_id: int) -> CityAdminImportJob:
    """The only way a runner (run_city_import_job, run_snapshot_refresh_job,
    etc.) may obtain the row it operates on. Requires the EXACT job_id the
    caller already claimed/created — never re-derives "the latest job for
    this city", which is exactly what let a runner started for one launch
    silently pick up a different, newer row created for the same city in
    the meantime. Raises if the row doesn't exist or belongs to a
    different city (defensive: callers must never mix up city_id/job_id).

    Requires status == "running": the row must already have been claimed
    by claim_queued_job() (worker path) or transitioned by the caller
    itself in the SAME atomic step it was created in (see
    run_city_import_job's own job_id-less direct-run path). A runner must
    never perform its own queued -> running transition — the second
    review round found that doing so let the row sit queued/unlocked
    between claim and run, so a second worker could claim the same row."""
    job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job is None:
        raise ValueError(f"Задача импорта #{job_id} не найдена")
    if int(job.city_id) != int(city_id):
        raise ValueError(f"Задача импорта #{job_id} принадлежит другому городу")
    if job.status != "running":
        raise ValueError(f"Задача импорта #{job_id} не в статусе running (текущий статус: {job.status})")
    return job


def claim_queued_job(db: Session, *, job_id: int, worker_id: str, actor_id: str | None = None) -> CityAdminImportJob:
    """The ONE atomic claim operation. Locks the exact row (SELECT ...
    FOR UPDATE), and — while still holding that lock, in the same
    transaction — transitions queued -> running, sets started_at and
    claimed_by exactly once, and writes the worker_job_claimed log event.
    All of this is committed together before the lock is released.

    This replaces the previous two-step sequence (select under
    FOR UPDATE SKIP LOCKED, commit only a log entry, let the runner do its
    own queued -> running later): that released the row lock while the row
    was still status="queued", started_at=NULL, so a second worker's own
    SKIP LOCKED scan — run after the first worker's SELECT committed but
    before its runner got around to transitioning the row — could select
    and claim the very same row a second time.

    Raises ValueError if the row is missing or already claimed/terminal
    (status != "queued") by the time the lock is acquired — the caller
    (run_queued_import_jobs) must treat that as "someone else already
    claimed it" and move on, not retry."""
    from services.system_log_service import write_system_log

    job = (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.id == job_id)
        .with_for_update()
        .first()
    )
    if job is None:
        raise ValueError(f"Задача импорта #{job_id} не найдена")
    if job.status != "queued" or job.started_at is not None or job.finished_at is not None:
        raise ValueError(f"Задача импорта #{job_id} уже не в состоянии queued (status={job.status})")
    claim_time = datetime.utcnow()
    queued_seconds = max(0, int((claim_time - job.created_at).total_seconds())) if job.created_at else None
    _transition(db, job, "running", actor_id=actor_id)
    job.started_at = claim_time
    job.claimed_by = worker_id
    city = db.query(City).filter(City.id == job.city_id).first()
    # module="import_worker" (not city_import) — worker_job_claimed is
    # part of the worker-lifecycle event stream _log_worker_decision/
    # _worker_lifecycle_fields already read from, and the diagnostic view
    # segments it alongside worker_job_finished/worker_job_failed by that
    # module. Writing it under city_import instead would silently split
    # one job's worker timeline across two modules.
    write_system_log(
        db,
        level="info",
        module="import_worker",
        message=f"Import worker claiming job #{job.id} (worker_id={worker_id})",
        details={"event": "worker_job_claimed", "job_id": job.id, "city_id": job.city_id, "source": job.source, "worker_id": worker_id, "status": job.status, "queued_seconds": queued_seconds},
        city_slug=city.slug if city is not None else None,
        request_id=str(job.id),
        actor_id=actor_id,
        commit=False,
    )
    db.commit()
    db.refresh(job)
    return job


def _active_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id, CityAdminImportJob.status.in_(("queued", "running")))
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )


def _latest_terminal_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    from services.admin_city_import_job_payload import _latest_job
    job = _latest_job(db, city_id)
    if job is not None and job.status in TERMINAL_STATUSES:
        return job
    return None


def _preserved_snapshot_context(job: CityAdminImportJob | None, source: str) -> dict[str, object]:
    if job is None or source != SOURCE_SNAPSHOT_REFRESH:
        return {}
    previous = dict(job.step_details or {})
    preserved: dict[str, object] = {}
    photo_result = previous.get("latest_photo_enrichment") or previous.get("photo_enrichment")
    if isinstance(photo_result, dict):
        preserved["latest_photo_enrichment"] = photo_result
        preserved["photo_enrichment"] = photo_result
    address_result = previous.get("latest_address_enrichment") or previous.get("address_enrichment")
    if isinstance(address_result, dict):
        preserved["latest_address_enrichment"] = address_result
        preserved["address_enrichment"] = address_result
    auto_repair = previous.get("auto_repair")
    if isinstance(auto_repair, dict):
        preserved["auto_repair"] = auto_repair
    return preserved


def _enqueue_job(db: Session, *, city: City, source: str, actor_id: str | None) -> CityAdminImportJob:
    """Immutable enqueue (fix for CityAdminImportJob lifecycle invariant #1:
    one admin launch = one new row).

    Concurrency-safe idempotent winner selection, two layers deep:

    1. SELECT ... FOR UPDATE on the CITY row itself (not the active-job
       query) serializes every enqueue attempt for this city, including
       the "no existing active row" case. Locking only the active-job
       query (the original approach) does not serialize two transactions
       that both see zero matching rows — a row lock only blocks readers
       of rows that already exist, so two concurrent enqueue calls could
       both pass the "no active job" check before either had inserted
       anything. Locking the city row means every enqueue attempt for
       that city, including the very first one, contends for the exact
       same lock and is strictly ordered.
    2. The partial unique index (uq_city_admin_import_jobs_active_city,
       see migration d4e8a1f6b3c9) is a second line of defence at the
       database level, for any process/session that reaches the insert
       without holding the city lock (e.g. a future code path, or a
       different isolation level). A unique-violation IntegrityError here
       is caught, the transaction is rolled back, and the actual winning
       active row is loaded fresh and reported via a truthful
       DuplicateActiveJobError — never left as an unhandled crash.

    A terminal row for this city (any previous launch/retry) is NEVER
    reused or reset — a brand new row is always inserted, with
    previous_job_id pointing at the most recent terminal row so the retry
    chain is reconstructible without guessing."""
    from sqlalchemy.exc import IntegrityError

    db.query(City).filter(City.id == city.id).with_for_update().first()
    active = (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city.id, CityAdminImportJob.status.in_(("queued", "running")))
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )
    if active is not None:
        raise DuplicateActiveJobError(city_id=city.id, job_id=active.id, job_status=active.status, source=active.source)
    previous = _latest_terminal_job(db, city.id)
    scopes = db.query(CityImportScope).filter_by(city_id=city.id, enabled=True).count()
    preserved = _preserved_snapshot_context(previous, source)
    job = CityAdminImportJob(
        city_id=city.id,
        previous_job_id=previous.id if previous is not None else None,
        status="queued",
        source=source,
        scopes_total=scopes,
        current_step=STEP_QUEUED,
        step_details={"city_state_before_import": {"launch_status": city.launch_status, "is_active": bool(city.is_active)}, **preserved},
        retry_count=(int(previous.retry_count) + 1) if previous is not None else 0,
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = (
            db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.city_id == city.id, CityAdminImportJob.status.in_(("queued", "running")))
            .order_by(CityAdminImportJob.created_at.desc())
            .first()
        )
        if winner is None:
            # Extremely unlikely (the conflicting row would have to have
            # been rolled back or terminalized between our INSERT failing
            # and this re-read), but never silently swallow it — the
            # caller must see a real error either way.
            raise
        raise DuplicateActiveJobError(city_id=city.id, job_id=winner.id, job_status=winner.status, source=winner.source)
    log_import_event(
        db, event="import_job_created", city_slug=city.slug, actor_id=actor_id,
        message=f"Создана задача {source} #{job.id}" + (f" (повтор #{previous.id})" if previous is not None else ""),
        details={"job_id": job.id, "scopes_total": scopes, "source": source, "previous_job_id": previous.id if previous is not None else None},
        job_id=job.id,
    )
    return job


def _resolve_run_job(db: Session, *, city_id: int, job_id: int | None) -> CityAdminImportJob:
    """Resolve the exact row a run_*_job runner must operate on.

    job_id is REQUIRED — enqueue (creating a row) and execute (running a
    row) are two separate operations, and no runner may bridge them by
    auto-selecting "the active row" or auto-creating a fresh one. Every
    execution path (admin API, background task, CLI) must first obtain a
    job_id from claim_queued_job() (the worker path) or from the row it
    itself just created via _enqueue_job (the synchronous admin-router
    path), then pass that exact job_id here. load_job_for_run further
    requires the row's status already be "running" — a runner never
    performs its own queued -> running transition (see claim_queued_job's
    docstring for why that specific gap let two workers claim the same
    row)."""
    if job_id is None:
        raise ValueError("job_id обязателен: раннер не может сам выбирать или создавать задачу")
    return load_job_for_run(db, job_id=job_id, city_id=city_id)


def retry_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    """Immutable retry (fix for lifecycle invariant #2: one retry = one new
    row with previous_job_id pointing at the prior row). Replaces the old
    reset_import_job_to_queued, which reused/reset the SAME row — the
    exact mechanism behind the production Job #1 corruption. Only valid
    when the city's latest job is itself terminal (not queued/running);
    _enqueue_job's own active-row lock already rejects a concurrent retry
    against a still-active job with the correct DuplicateActiveJobError."""
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def run_city_import_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    # _resolve_run_job/load_job_for_run already requires status == "running"
    # — the row was already claimed (queued -> running) atomically by
    # claim_queued_job before this function was ever called. This function
    # must never perform that transition itself.
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    # Fixed once, right after the row is resolved: this run's proof of
    # ownership for its eventual finalize_import_job call. claim_queued_job set
    # claimed_by in the same transaction as queued -> running, so this is
    # exactly the identity that claimed this exact row — never re-read
    # later from a possibly-stale in-memory `job` object.
    expected_claimed_by = job.claimed_by
    if job.current_step == STEP_CANCELLED:
        raise ValueError("Задача отменена. Создайте новую через повтор.")
    # finished_at/last_error are guaranteed NULL here: the immutable-row
    # lifecycle (_enqueue_job) always inserts a fresh row per launch/retry,
    # and claim_queued_job performs the queued -> running transition
    # exactly once per row — there is no prior execution's terminal state
    # on this row to reset. Terminal fields are written exactly once, by
    # finalize_import_job, at the end of this function.
    job.source = SOURCE_FULL_IMPORT
    job.scopes_total = db.query(CityImportScope).filter_by(city_id=city_id, enabled=True).count()
    log_import_event(db, event="import_job_started", city_slug=city.slug, actor_id=actor_id, message=f"Старт полного pipeline #{job.id}", details={"job_id": job.id, "source": job.source}, job_id=job.id)
    db.commit()
    try:
        # run_enrichment_pipeline never writes job.status — it returns this
        # phase's own outcome in legacy["status"] instead, so job.status
        # stays "running" for the whole call (see the function's own
        # comment). job.finished_at is likewise left untouched here.
        legacy = run_enrichment_pipeline(db, job=job, city=city, actor_id=actor_id, force=True, notify_completion=False)
        db.refresh(job)
        db.refresh(city)
        legacy_status = str(legacy.get("status") or "success")
        ids = [int(v) for v in legacy.get("changed_place_ids", [])]
        warnings = list((job.step_details or {}).get("warnings") or [])
        saved = (job.places_found, job.places_saved, job.scopes_succeeded)
        source = _foundation(db, city, job, actor_id, ids)
        # run_foundation_pipeline likewise never writes job.status — its
        # own outcome is in job.step_details["source_enrichment_status"].
        source_status = str((job.step_details or {}).get("source_enrichment_status") or "success")
        job.places_found, job.places_saved, job.scopes_succeeded = saved
        auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=ids)
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}
        places = db.query(Place).filter(Place.id.in_(ids)).order_by(Place.id).all() if ids else []
        record_place_changes(db, job=job, places=places, since=job.started_at or datetime.utcnow())
        if source_status in {"partial_success", "success_with_warnings", "failed"} or int(source.get("failed") or 0) > 0:
            warnings.append({"step": "source_enrichment", "error": f"Ошибок этапов обогащения: {int(source.get('failed') or 0)}"})
        if legacy_status in {"partial_success", "failed"}:
            warnings.append({"step": "collection_and_legacy_enrichment", "error": f"Статус этапа сбора/обогащения: {legacy_status}", "last_error": job.last_error})
        step_details = {**dict(job.step_details or {}), "warnings": warnings, "changed_place_ids": ids, "has_changes": bool(ids), "auto_repair": auto_repair, "unified_pipeline": {"collection_and_legacy_enrichment": legacy, "source_enrichment": source, "readiness_score": readiness.get("readiness_score"), "auto_repair": auto_repair, "completed": True}}
        combined_status = _combine_status(legacy_status, source_status, "success_with_warnings" if warnings else "success")
        publication = finalize_import_publication(
            db,
            city=city,
            job=job,
            place_ids=ids,
            import_status=combined_status,
        )
        job_last_error = job.last_error
        if publication.get("status") == "failed" and combined_status in {"success", "success_with_warnings"}:
            combined_status = "partial_success"
            job_last_error = f"publication_stage_failed:{','.join(publication.get('reasons', []))}"
        finished_at = datetime.utcnow()
        # Atomic, database-authoritative finalization: re-locks the exact
        # row by job_id, verifies status=="running" AND claimed_by still
        # matches this run under that lock, and only then writes status +
        # every terminal field together. If the row left "running" while
        # we were working (e.g. a concurrent mark_stalled_import_jobs sweep
        # or an admin cancel — possibly committed by an entirely different
        # PostgreSQL connection, which this Session's stale `job` object
        # would never observe on its own), result.ok is False and NONE of
        # the fields below are written — the row's real terminal state
        # (set by whoever actually holds the lock first) is never
        # overwritten with this run's own late-arriving result.
        result = finalize_import_job(
            db, job_id=job.id, new_status=combined_status, expected_claimed_by=expected_claimed_by, actor_id=actor_id,
            fields={
                "finished_at": finished_at,
                "last_error": job_last_error,
                "step_details": {**step_details, "publication_finalize": publication},
            },
        )
        if result.ok:
            job = result.job
            city.last_import_at = finished_at
            _refresh_snapshot_light(db, city=city, job=job, source="import_worker_finished")
            log_import_event(db, event="unified_import_pipeline_finished", city_slug=city.slug, actor_id=actor_id, message=f"Полный pipeline #{job.id}: {len(ids)} изменений; auto-repair {auto_repair.get('repaired_count', 0)}; публикация города сохранена", details={"job_id": job.id, "changed_places": len(ids), "warnings": warnings, "auto_repair": auto_repair, "city_launch_status": city.launch_status, "city_is_active": bool(city.is_active)}, job_id=job.id)
        else:
            # finalize_import_job rejected the write and expunged the
            # stale `job` object from this Session — it is no longer
            # session-managed and must never be touched again (including
            # db.refresh below). Re-fetch a fresh, session-attached row so
            # the function's return value is always usable by its caller.
            job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        db.commit()
        if result.ok:
            job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).first()
            _alert(db, city, job, len(ids), readiness, warnings)
    except Exception as exc:
        db.rollback()
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        city = db.query(City).filter(City.id == city_id).first()
        total = db.query(Place).filter(Place.city_id == city_id).count()
        ids = [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])] if job else []
        finalized = False
        if job is not None:
            finished_at = datetime.utcnow()
            # This run's own changed_place_ids (recorded before the crash) is the
            # only truthful signal that *this* run made meaningful progress.
            # total > 0 (city has any place, possibly from a prior run) must not
            # by itself downgrade a hard failure of this run to partial_success.
            result = finalize_import_job(
                db, job_id=job.id, new_status="partial_success" if ids else "failed",
                expected_claimed_by=expected_claimed_by, actor_id=actor_id,
                fields={"finished_at": finished_at, "last_error": str(exc)[:2000]},
            )
            if result.ok:
                job = result.job
                finalized = True
                if city is not None:
                    city.last_import_at = finished_at
                    _refresh_snapshot_light(db, city=city, job=job, source="import_pipeline_failed")
            else:
                # Same reasoning as the success path above: the stale
                # object was expunged by finalize_import_job's rejection.
                job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        db.commit()
        if finalized:
            job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).first()
            send_admin_alert(title="Import completed with warnings" if total > 0 else "Import pipeline failed", message=f"Pipeline прерван. Изменённых мест: {len(ids)}. Публикация города не изменялась.", level="warning" if total > 0 else "error", city_slug=city.slug if city else None, job_id=int(job.id) if job else None, details={"status": job.status if job else "failed", "places_total": total, "changed_places": len(ids), "city_launch_status": city.launch_status if city else None, "city_is_active": bool(city.is_active) if city else None, "warnings": [{"step": "unified_pipeline", "error": str(exc)[:1000]}]})
    db.refresh(job)
    return job


def run_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    expected_claimed_by = job.claimed_by
    job.source = SOURCE_SNAPSHOT_REFRESH
    job.current_step = "snapshot_refresh"
    db.commit()
    # Computed as a pure, non-writing step (no separate commit on this
    # possibly-soon-to-be-stale `job` object) and folded into
    # finalize_import_job's own atomic fields= write below — a prior
    # version wrote step_details here via its own db.commit() BEFORE the
    # row was locked, which was itself an unprotected terminal-adjacent
    # write racing against a concurrent stall/cancel.
    step_details, _snapshot = _build_light_snapshot_step_details(db, city=city, job=job, source="snapshot_refresh_job")
    # Atomic, database-authoritative finalization — see finalize_import_job's
    # docstring. If the row left "running" while the snapshot refresh was
    # in flight (e.g. a concurrent stall-recovery sweep committed by a
    # different connection), result.ok is False and nothing is written —
    # whatever truthful terminal state got there first is never overwritten.
    result = finalize_import_job(
        db, job_id=job.id, new_status="success", expected_claimed_by=expected_claimed_by, actor_id=actor_id,
        fields={"finished_at": datetime.utcnow(), "current_step": "snapshot_ready", "step_details": step_details},
    )
    db.commit()
    job = result.job if result.ok else db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    db.refresh(job)
    return job


def _enrichment_prerequisites(db: Session, *, city: City) -> dict[str, object]:
    """Shared prerequisite check for standalone admin enrichment actions
    (Добрать фото / Добрать адреса). These do not go through run_enrichment_pipeline,
    so unlike the main import they had no check that collecting_places ever
    produced usable places before scanning — this made "eligible but never run"
    indistinguishable from "ran and found nothing to do"."""
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    blocked_reason = None if places_total > 0 else "no_places_in_city"
    return {
        "places_total": places_total,
        "blocked_reason": blocked_reason,
        "ok": blocked_reason is None,
    }


def run_address_enrichment_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    expected_claimed_by = job.claimed_by
    job.source = SOURCE_ADDRESS_ENRICHMENT
    job.current_step = "finding_addresses"
    db.commit()
    prerequisites = _enrichment_prerequisites(db, city=city)
    if not prerequisites["ok"]:
        step_details = {
            **dict(job.step_details or {}),
            "address_enrichment": {"scanned_places": 0, "updated": 0, "checked": 0, "blocked_reason": prerequisites["blocked_reason"]},
            "prerequisites": prerequisites,
        }
        finalize_result = finalize_import_job(
            db, job_id=job.id, new_status="failed", expected_claimed_by=expected_claimed_by, actor_id=actor_id,
            fields={
                "finished_at": datetime.utcnow(),
                "current_step": STEP_ERROR,
                "last_error": f"Добор адресов заблокирован: {prerequisites['blocked_reason']}",
                "step_details": step_details,
            },
        )
        if finalize_result.ok:
            log_import_event(db, event="address_enrichment_blocked", city_slug=city.slug, actor_id=actor_id, level="warning", message=f"Добор адресов #{job.id} заблокирован: {prerequisites['blocked_reason']}", details={"job_id": job.id, "city_id": city.id, "source": SOURCE_ADDRESS_ENRICHMENT, "prerequisites": prerequisites}, job_id=job.id)
        db.commit()
        job = finalize_result.job if finalize_result.ok else db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        db.refresh(job)
        return job
    backfill_result = run_address_backfill(["--city", city.slug, "--limit", str(ADDRESS_LIMIT), "--apply"])
    auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=[])
    step_details = {**dict(job.step_details or {}), "address_enrichment": backfill_result, "auto_repair": auto_repair, "prerequisites": prerequisites}
    deadline_exceeded = bool(isinstance(backfill_result, dict) and backfill_result.get("deadline_exceeded"))
    errors = int(backfill_result.get("errors") or 0) if isinstance(backfill_result, dict) else 0
    last_error = None
    if deadline_exceeded:
        checked = int(backfill_result.get("checked") or 0) if isinstance(backfill_result, dict) else 0
        last_error = f"Добор адресов остановлен по таймауту выполнения после проверки {checked} мест."
    finalize_result = finalize_import_job(
        db, job_id=job.id, new_status="success_with_warnings" if deadline_exceeded or errors > 0 else "success",
        expected_claimed_by=expected_claimed_by, actor_id=actor_id,
        fields={
            "finished_at": datetime.utcnow(),
            "current_step": "snapshot_refresh",
            "last_error": last_error,
            "step_details": step_details,
        },
    )
    if finalize_result.ok:
        job = finalize_result.job
        db.commit()
        _refresh_snapshot_light(db, city=city, job=job, source="address_enrichment_finished")
    else:
        db.commit()
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    db.refresh(job)
    return job


def run_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    expected_claimed_by = job.claimed_by
    job.source = SOURCE_PHOTO_ENRICHMENT
    job.current_step = "finding_images"
    db.commit()
    prerequisites = _enrichment_prerequisites(db, city=city)
    if not prerequisites["ok"]:
        photo_diagnostics = build_photo_enrichment_diagnostics(db, city, enrichment_result=None, step_status="blocked", scan_limit=IMAGE_LIMIT)
        step_details = {
            **dict(job.step_details or {}),
            "photo_enrichment": {"scanned_places": 0, "created": 0, "candidates_found": 0, "blocked_reason": prerequisites["blocked_reason"]},
            "photo_diagnostics": photo_diagnostics,
            "prerequisites": prerequisites,
        }
        finalize_result = finalize_import_job(
            db, job_id=job.id, new_status="failed", expected_claimed_by=expected_claimed_by, actor_id=actor_id,
            fields={
                "finished_at": datetime.utcnow(),
                "current_step": STEP_ERROR,
                "last_error": f"Добор фото заблокирован: {prerequisites['blocked_reason']}",
                "step_details": step_details,
            },
        )
        if finalize_result.ok:
            log_import_event(db, event="photo_enrichment_blocked", city_slug=city.slug, actor_id=actor_id, level="warning", message=f"Добор фото #{job.id} заблокирован: {prerequisites['blocked_reason']}", details={"job_id": job.id, "city_id": city.id, "source": SOURCE_PHOTO_ENRICHMENT, "prerequisites": prerequisites}, job_id=job.id)
        db.commit()
        job = finalize_result.job if finalize_result.ok else db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        db.refresh(job)
        return job
    enrich_result = run_image_enrich(["--city", city.slug, "--limit", str(IMAGE_LIMIT), "--apply"])
    if isinstance(enrich_result, dict) and "photo_diagnostics" not in enrich_result:
        enrich_result = attach_photo_diagnostics_to_summary(db, city, enrich_result, scan_limit=IMAGE_LIMIT)
    scanned = int(enrich_result.get("scanned_places") or 0) if isinstance(enrich_result, dict) else 0
    created = int(enrich_result.get("created") or 0) if isinstance(enrich_result, dict) else 0
    errors = enrich_result.get("errors") if isinstance(enrich_result, dict) else []
    provider_status = enrich_result.get("provider_status") if isinstance(enrich_result, dict) else None
    photo_diagnostics = enrich_result.get("photo_diagnostics") if isinstance(enrich_result, dict) else build_photo_enrichment_diagnostics(db, city, enrichment_result=enrich_result if isinstance(enrich_result, dict) else None, scan_limit=IMAGE_LIMIT)
    auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=[])
    step_details = {**dict(job.step_details or {}), "photo_enrichment": enrich_result, "photo_diagnostics": photo_diagnostics, "auto_repair": auto_repair, "prerequisites": prerequisites}
    last_error = None
    if isinstance(enrich_result, dict) and enrich_result.get("deadline_exceeded"):
        last_error = f"Добор фото остановлен по таймауту выполнения после просмотра {scanned} мест."
    finalize_result = finalize_import_job(
        db, job_id=job.id,
        new_status="success_with_warnings" if created <= 0 and str(photo_diagnostics.get("provider_status") or "") not in {"success", ""} else "success",
        expected_claimed_by=expected_claimed_by, actor_id=actor_id,
        fields={
            "finished_at": datetime.utcnow(),
            "current_step": "snapshot_refresh",
            "last_error": last_error,
            "step_details": step_details,
            "places_found": scanned,
            "places_saved": created,
            "total_items": scanned,
            "processed_items": scanned,
            "successful_items": scanned,
            "failed_items": len(errors or []) if isinstance(errors, list) else 0,
        },
    )
    if finalize_result.ok:
        job = finalize_result.job
        log_import_event(db, event="photo_enrichment_finished", city_slug=city.slug, actor_id=actor_id, message=f"Добор фото #{job.id}: создано {created}, просмотрено {scanned}, provider={provider_status or 'unknown'}", details={"job_id": job.id, "source": SOURCE_PHOTO_ENRICHMENT, "photo_enrichment": enrich_result, "photo_diagnostics": photo_diagnostics, "auto_repair": auto_repair}, job_id=job.id)
        db.commit()
        _refresh_snapshot_light(db, city=city, job=job, source="photo_enrichment_finished")
    else:
        db.commit()
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    db.refresh(job)
    return job


def _build_light_snapshot_step_details(db: Session, *, city: City, job: CityAdminImportJob, source: str) -> tuple[dict[str, object], dict[str, object]]:
    """Pure computation, no write: returns (updated step_details, snapshot).
    Split out from _refresh_snapshot_light so a caller that still needs to
    go through finalize_import_job can fold the resulting step_details into
    that single atomic write instead of writing it separately beforehand on
    a not-yet-locked row."""
    total = db.query(Place).filter(Place.city_id == city.id).count()
    published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
    without_address = db.query(Place).filter(Place.city_id == city.id, Place.address.is_(None)).count()
    without_photo = db.query(Place).filter(Place.city_id == city.id, Place.image_url.is_(None)).count()
    without_description = db.query(Place).filter(Place.city_id == city.id, Place.short_description.is_(None)).count()
    pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    def pct(missing: int) -> float:
        return round(((total - missing) / total) * 100, 1) if total else 0.0
    coverage = {"places_total": int(total), "places_published": int(published), "places_unpublished": max(int(total) - int(published), 0), "without_address": int(without_address), "without_photo": int(without_photo), "without_description": int(without_description), "address_coverage_pct": pct(int(without_address)), "photo_coverage_pct": pct(int(without_photo)), "description_coverage_pct": pct(int(without_description)), "pending_photos": int(pending_photos)}
    existing_changes = dict(job.step_details or {}).get("change_summary")
    changes = existing_changes if isinstance(existing_changes, dict) else {"job_id": job.id, "city_id": city.id, "city_slug": city.slug, **{key: 0 for key in CHANGE_TYPES}}
    changes = {**changes, "total_changes": sum(int(changes.get(key) or 0) for key in CHANGE_TYPES)}
    auto_repair = dict(job.step_details or {}).get("auto_repair")
    snapshot = {"version": 1, "source": source, "taken_at": datetime.utcnow().isoformat(), "city_id": city.id, "city_slug": city.slug, "job_id": job.id, "data_coverage": coverage, "change_summary": changes, "auto_repair": auto_repair if isinstance(auto_repair, dict) else None}
    details = dict(job.step_details or {})
    details[SNAPSHOT_KEY] = snapshot
    details["data_coverage"] = coverage
    details["change_summary"] = changes
    return details, snapshot


def _refresh_snapshot_light(db: Session, *, city: City, job: CityAdminImportJob, source: str) -> dict[str, object]:
    """Side-effecting wrapper for callers AFTER a successful
    finalize_import_job — safe because `job` here is always the freshly
    locked/reloaded result.job, still within the same open transaction
    finalize_import_job's own SELECT ... FOR UPDATE started, so this
    additional step_details write cannot race with anything: the row's
    lock is held continuously from the finalize call through this
    function's own commit(). Never call this BEFORE finalize_import_job —
    use _build_light_snapshot_step_details directly and fold the result
    into finalize_import_job's own `fields=` instead (see
    run_snapshot_refresh_job)."""
    details, snapshot = _build_light_snapshot_step_details(db, city=city, job=job, source=source)
    job.step_details = details
    job.updated_at = datetime.utcnow()
    db.commit()
    return snapshot


def _run_auto_repair(db: Session, *, city: City, job: CityAdminImportJob, changed_place_ids: list[int]) -> dict[str, object]:
    query = db.query(Place).filter(Place.city_id == city.id)
    if changed_place_ids:
        query = query.filter(Place.id.in_(changed_place_ids))
    else:
        query = query.order_by(Place.id.desc()).limit(AUTO_REPAIR_CITY_SCAN_LIMIT)
    places = query.all()
    summary = PlaceAutoRepairService().repair_places(places)
    payload = _serialize_auto_repair_summary(summary)
    details = dict(job.step_details or {})
    details["auto_repair"] = payload
    job.step_details = details
    log_import_event(db, event="place_auto_repair_finished", city_slug=city.slug, actor_id=None, message=f"Auto-repair #{job.id}: repaired={summary.repaired_count}, review={summary.needs_review_count}, skipped={summary.skipped_count}", details={"job_id": job.id, "auto_repair": payload}, job_id=job.id)
    return payload


def _serialize_auto_repair_summary(summary: PlaceAutoRepairSummary) -> dict[str, object]:
    return {"repaired_count": int(summary.repaired_count), "needs_review_count": int(summary.needs_review_count), "skipped_count": int(summary.skipped_count), "by_reason": dict(summary.by_reason), "by_category": dict(summary.by_category), "items": [item.__dict__ for item in summary.items[:200]]}


def _foundation(db, city, job, actor_id, ids):
    kwargs = {"db": db, "city": city, "job": job, "actor": actor_id}
    if "place_ids" in inspect.signature(run_foundation_pipeline).parameters:
        kwargs["place_ids"] = ids
    return run_foundation_pipeline(**kwargs)


def _alert(db, city, job, changed, readiness, warnings):
    total = db.query(Place).filter(Place.city_id == city.id).count()
    auto_repair = dict(job.step_details or {}).get("auto_repair")
    send_admin_alert(title="Import completed with warnings" if warnings else "Import pipeline finished", message=f"{city.name}: {changed} мест обновлено. Публикация города сохранена." if changed else f"{city.name}: изменений нет, публикация сохранена.", level="warning" if warnings else "info", city_slug=city.slug, job_id=int(job.id), details={"status": job.status, "source": job.source, "places_total": total, "changed_places": changed, "city_launch_status": city.launch_status, "city_is_active": bool(city.is_active), "readiness": readiness, "auto_repair": auto_repair if isinstance(auto_repair, dict) else None, "warnings": warnings})


def run_enrichment_only_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    expected_claimed_by = job.claimed_by
    # finished_at/last_error are guaranteed NULL here — see the equivalent
    # comment in run_city_import_job.
    job.source = SOURCE_ENRICHMENT_ONLY
    db.commit()
    try:
        # run_enrichment_only_pipeline never writes job.status — its own
        # outcome is in the returned dict's "status" key.
        enrichment_only_result = run_enrichment_only_pipeline(db, job=job, city=city, actor_id=actor_id)
        db.refresh(job)
        enrichment_only_status = str(enrichment_only_result.get("status") or "success")
        ids = [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])]
        _foundation(db, city, job, actor_id, ids)
        # run_foundation_pipeline likewise never writes job.status.
        source_status = str((job.step_details or {}).get("source_enrichment_status") or "success")
        auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=ids)
        step_details = {**dict(job.step_details or {}), "auto_repair": auto_repair}
        # Atomic, database-authoritative finalization — see finalize_import_job.
        # If the row left "running" while this pipeline was in flight (e.g.
        # a concurrent stall-recovery sweep or admin cancel, possibly
        # committed by an entirely different connection), result.ok is
        # False and nothing is written — whatever truthful terminal state
        # got there first is never overwritten.
        result = finalize_import_job(
            db, job_id=job.id, new_status=_combine_status(enrichment_only_status, source_status, "success"),
            expected_claimed_by=expected_claimed_by, actor_id=actor_id,
            fields={"finished_at": datetime.utcnow(), "step_details": step_details},
        )
        if result.ok:
            job = result.job
            db.commit()
            _refresh_snapshot_light(db, city=city, job=job, source="enrichment_only_finished")
        else:
            db.commit()
            job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    except Exception as exc:
        finished_at = datetime.utcnow()
        details = dict(job.step_details or {})
        details["worker_exception"] = {"error": str(exc)[:1000], "failed_at": finished_at.isoformat()}
        result = finalize_import_job(
            db, job_id=job.id, new_status="failed", expected_claimed_by=expected_claimed_by, actor_id=actor_id,
            fields={
                "current_step": STEP_ERROR,
                "last_error": str(exc)[:2000],
                "failed_items": max(int(job.failed_items or 0), 1),
                "finished_at": finished_at,
                "updated_at": finished_at,
                "step_details": details,
            },
        )
        db.commit()
        job = result.job if result.ok else db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        raise
    db.refresh(job)
    return job


def cancel_import_job(db: Session, *, city_id: int, actor_id: str, job_id: int) -> CityAdminImportJob:
    """Administrative action, routed through the same canonical
    finalize_import_job() every other terminal write uses —
    _FINALIZE_FROM_STATUSES allows "queued" -> "cancelled" specifically so
    a job no worker ever claimed can also be cancelled through this one
    lock-check-write primitive, instead of a second, separately-maintained
    implementation of the same discipline.

    An admin cancel intentionally overrides whoever currently "owns" the
    row (no expected_claimed_by is passed) — that is the whole point of a
    manual cancel action.

    The city_id ownership check is a cheap unlocked pre-check: it exists to
    reject "you're cancelling the wrong city's job" caller mistakes, not to
    participate in the concurrency contract — the actual race-safety
    (status/finished_at re-verified under FOR UPDATE) is entirely
    finalize_import_job's responsibility."""
    job_city_id = db.query(CityAdminImportJob.city_id).filter(CityAdminImportJob.id == job_id).scalar()
    if job_city_id is None:
        raise ValueError(f"Задача импорта #{job_id} не найдена")
    if int(job_city_id) != int(city_id):
        raise ValueError(f"Задача импорта #{job_id} принадлежит другому городу")
    now = datetime.utcnow()
    result = finalize_import_job(
        db, job_id=job_id, new_status="cancelled", actor_id=actor_id,
        fields={"current_step": STEP_CANCELLED, "cancelled_at": now, "finished_at": now},
    )
    if not result.ok:
        # Either genuinely already terminal, or left queued/running out
        # from under this call between whatever the caller last observed
        # and finalize_import_job acquiring the lock — either way,
        # truthfully report "already finished" rather than overwriting
        # real state.
        raise ValueError("Задача уже завершена")
    job = result.job
    city = db.query(City).filter(City.id == city_id).first()
    if city:
        log_import_event(db, event="import_job_cancelled", city_slug=city.slug, actor_id=actor_id, message=f"Импорт #{job.id} отменён без изменения публикации города", details={"job_id": job.id, "source": job.source}, job_id=job.id)
    db.commit()
    db.refresh(job)
    return job
