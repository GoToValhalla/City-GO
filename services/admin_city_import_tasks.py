"""Фоновый запуск import jobs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import os
import uuid

from db.session import SessionLocal
from core.config import settings
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_job_service import (
    SOURCE_ADDRESS_ENRICHMENT,
    SOURCE_ENRICHMENT_ONLY,
    SOURCE_FULL_IMPORT,
    SOURCE_PHOTO_ENRICHMENT,
    SOURCE_SNAPSHOT_REFRESH,
    finalize_import_job,
    claim_queued_job,
    run_address_enrichment_job,
    run_city_import_job,
    run_enrichment_only_job,
    run_photo_enrichment_job,
    run_snapshot_refresh_job,
)
from services.import_pipeline.progress import is_stalled
from services.import_pipeline.steps import STEP_ERROR
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.import_worker_thresholds import effective_thresholds
from services.system_log_service import write_system_log

HEAVY_IMPORT_SOURCES = {SOURCE_FULL_IMPORT, SOURCE_ENRICHMENT_ONLY}


def _worker_id() -> str:
    """Opaque per-process identity attached to a job at claim time
    (CityAdminImportJob.claimed_by) — distinguishes which worker process
    actually claimed a row, for diagnostics; not used for any locking
    decision (the row lock itself is what makes the claim atomic)."""
    return f"{os.getpid()}-{uuid.uuid4().hex[:8]}"


def _available_memory_mb() -> int | None:
    try:
        with open("/proc/meminfo") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        return None
    return None


def _safe_mode_block_reason(job: CityAdminImportJob) -> str | None:
    if not settings.import_worker_safe_mode:
        return None
    source = str(job.source or "")
    if source not in HEAVY_IMPORT_SOURCES:
        return None
    if settings.import_worker_max_full_import_places_low_memory <= 0:
        return (
            "import-worker safety guard: full/heavy import jobs "
            f"(source={source}) are explicitly disabled in safe mode. Job not processed."
        )
    available = _available_memory_mb()
    job_claim_floor = effective_thresholds().job_claim_host_floor_mb
    if available is None or available < job_claim_floor:
        return (
            "import-worker safety guard: available host memory "
            f"({available if available is not None else 'unknown'} MB) is below the configured "
            f"job-claim minimum ({job_claim_floor} MB). Job not processed."
        )
    return None


# F04: run_import_job_background / run_enrichment_job_background /
# run_all_cities_enrichment_background were removed. Each claimed and
# executed a CityAdminImportJob directly from a FastAPI BackgroundTasks
# callback (or, for the third, a raw function call) inside the API server
# process -- a second, unauthorized execution path that bypassed every
# import-worker guarantee (memory/runtime limits, lifecycle, ownership,
# observability, recovery). run_import_job_background was the only one
# with a real production caller (routers.admin.create_city_import); the
# other two had zero callers anywhere in the codebase. The admin API's
# contract is enqueue-only: only data/scripts/run_admin_import_worker.py
# (via run_queued_import_jobs below) may claim and execute a queued job.


def run_queued_import_jobs(
    *,
    actor_id: str = "import-worker",
    limit: int = 1,
    city_slug: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    limit = max(1, int(limit or 1))
    processed = 0
    failed = 0
    errors: list[dict[str, object]] = []
    claimed_jobs: list[dict[str, object]] = []
    with SessionLocal() as db:
        # dry_run never claims or mutates anything, so marking stalled jobs
        # (a mutation) must not happen either — it stays purely observational.
        stalled = 0 if dry_run else mark_stalled_import_jobs(db, actor_id=actor_id)
        # started_at/finished_at IS NULL, on top of status == "queued", is
        # the fix for the production Job #1 corruption: a row can end up
        # status="queued" while carrying started_at/finished_at from an
        # earlier, unrelated worker run (the old reset-in-place bug). Under
        # the new immutable lifecycle this combination should never occur
        # for a genuine new row, but the filter is what makes the claim
        # query itself refuse such a row rather than trusting status alone.
        query = db.query(CityAdminImportJob).filter(
            CityAdminImportJob.status == "queued",
            CityAdminImportJob.started_at.is_(None),
            CityAdminImportJob.finished_at.is_(None),
        )
        if city_slug:
            query = query.join(City, CityAdminImportJob.city_id == City.id).filter(City.slug == city_slug)
        query = query.order_by(CityAdminImportJob.created_at.asc(), CityAdminImportJob.id.asc())
        if dry_run:
            # No FOR UPDATE / SKIP LOCKED: a dry run must not take row locks
            # that could block a real worker from claiming the same job.
            jobs = query.limit(limit).all()
            queue = import_queue_summary(db)
            return {
                "processed": 0,
                "failed": 0,
                "stalled_marked": 0,
                "errors": [],
                "queue": queue,
                "dry_run": True,
                "would_process": [
                    {"job_id": int(job.id), "city_id": int(job.city_id), "source": str(job.source or "")}
                    for job in jobs
                ],
            }
        # No FOR UPDATE / SKIP LOCKED here: with limit > 1 those locks would
        # be released by this loop's OWN intermediate db.commit() calls
        # (status-not-queued skip, safe-mode block, claim-skip) long before
        # the loop reaches later rows in the same batch — a lock a
        # transaction no longer holds provides no protection, so relying on
        # it here was misleading rather than unsafe. The real, sole atomic
        # guard is claim_queued_job's own per-row SELECT ... FOR UPDATE,
        # acquired and released within one uninterrupted commit for each
        # job as the loop reaches it — see its docstring. This batch SELECT
        # only needs to name candidates; it does not need to hold them.
        jobs = query.limit(limit).all()
        if not jobs:
            running_query = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running")
            if city_slug:
                running_query = running_query.join(City, CityAdminImportJob.city_id == City.id).filter(City.slug == city_slug)
            running_count = running_query.count()
            _log_worker_decision(
                db,
                event="worker_no_queued_jobs",
                actor_id=actor_id,
                message=f"Import worker found no queued jobs; active running jobs: {running_count}",
                details={"limit": limit, "running": running_count, "stalled_marked": stalled, "city_slug": city_slug},
            )
            db.commit()
        for job in jobs:
            job_id = int(job.id)
            city_id = int(job.city_id)
            source = str(job.source or "")
            if job.status != "queued":
                _log_worker_decision(
                    db,
                    event="worker_claim_skipped",
                    actor_id=actor_id,
                    message=f"Import worker skipped job #{job_id}: status is {job.status}",
                    job=job,
                    details={"reason": "status_not_queued", "status": job.status, "limit": limit},
                )
                db.commit()
                continue
            block_reason = _safe_mode_block_reason(job)
            if block_reason is not None:
                # The job stays queued: this guard reflects a transient host
                # resource shortage, not a defect in the job itself. Marking
                # it failed would drop it from the queue and require manual
                # re-enqueueing once memory recovers; leaving it queued lets
                # the next worker run automatically pick it up again.
                _log_worker_decision(
                    db,
                    event="worker_job_blocked_safe_mode",
                    actor_id=actor_id,
                    level="warning",
                    message=f"Import worker skipped job #{job_id} (stays queued): {block_reason}",
                    job=job,
                    details={"reason": "safe_mode_resource_guard", "source": source, "limit": limit},
                )
                db.commit()
                send_admin_alert(
                    title="Import worker job blocked (safe mode)",
                    message=block_reason,
                    level="warning",
                    job_id=job_id,
                    details={"city_id": city_id, "source": source},
                )
                continue
            # Atomic claim: under the SAME row lock (SELECT ... FOR UPDATE,
            # re-acquired inside claim_queued_job) the row is transitioned
            # queued -> running, started_at/claimed_by are set, and
            # worker_job_claimed is logged — all committed together before
            # the lock is released. This replaces the previous two-step
            # sequence (commit a log entry here, let the runner do its own
            # queued -> running later) that left a claimed-looking row
            # still status=queued and unlocked for a second worker to claim.
            worker_id = _worker_id()
            try:
                job = claim_queued_job(db, job_id=job_id, worker_id=worker_id, actor_id=actor_id)
            except ValueError:
                # Someone else (another concurrent worker process) claimed
                # this exact row between our SELECT and our claim attempt —
                # not an error, just skip it and move to the next job.
                _log_worker_decision(
                    db,
                    event="worker_claim_skipped",
                    actor_id=actor_id,
                    message=f"Import worker skipped job #{job_id}: already claimed by another worker",
                    details={"reason": "already_claimed", "job_id": job_id, "limit": limit},
                )
                db.commit()
                continue
            # A SAVEPOINT taken before this job's own work: runners commit
            # internally on their own success paths (closing this SAVEPOINT
            # early, which is fine — nothing to roll back then), but never
            # commit right before raising. On failure we roll back to this
            # SAVEPOINT specifically, never the caller's own outer
            # transaction — production: the request-scoped SessionLocal();
            # tests: a shared fixture session whose already-committed setup
            # rows must survive. db.rollback() on that outer transaction
            # would instead discard it entirely, which is the prior defect.
            # Managed manually (not as a `with` block) because a runner's
            # own internal db.commit() closes the SAVEPOINT out from under
            # a context manager's __exit__, breaking any code — including
            # our own — that still expects to operate on it afterward.
            savepoint = db.begin_nested()
            try:
                # Every runner returns the row exactly as finalize_import_job
                # left it (freshly reloaded on success, or re-fetched fresh
                # after a rejected finalize expunged the pre-run object) --
                # that return value, not the `job` loaded before the call
                # above, is the only truthful post-run state. Reusing the
                # pre-run `job` here previously reported a stale "running"
                # status whenever finalize_import_job rejected the write
                # (lost ownership / already terminalized by a concurrent
                # stall-sweep or cancel), which the worker then misreported
                # as "max_runtime_without_terminal_progress" even though the
                # pipeline had actually finished and runtime had not expired.
                if source == SOURCE_ENRICHMENT_ONLY:
                    job = run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_SNAPSHOT_REFRESH:
                    job = run_snapshot_refresh_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_ADDRESS_ENRICHMENT:
                    job = run_address_enrichment_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_PHOTO_ENRICHMENT:
                    job = run_photo_enrichment_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                else:
                    job = run_city_import_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                processed += 1
                actual_status = str(job.status) if job is not None else "unknown"
                claimed_jobs.append({
                    "job_id": job_id,
                    "terminal_status": actual_status,
                    "claimed_by": job.claimed_by if job is not None else None,
                    "expected_claimed_by": worker_id,
                    "finished_at": job.finished_at.isoformat() if job is not None and job.finished_at else None,
                })
                _log_worker_decision(
                    db,
                    event="worker_job_finished",
                    actor_id=actor_id,
                    message=f"Import worker finished job #{job_id}",
                    job=job,
                    details={"final_status": actual_status, "source": source},
                )
                db.commit()
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                # SystemExit is deliberately caught here too: run_city_import_job's
                # call chain reaches run_due_import_jobs._targets(), a standalone
                # CLI script's helper that raises SystemExit when a city has no
                # matching import targets (e.g. its launch_status left
                # importing/imported/review_required after publication). SystemExit
                # subclasses BaseException, not Exception, so without this it skips
                # every handler up to and including the worker loop's own
                # `except Exception`, killing the whole worker process instead of
                # just failing this one job.
                # Roll back only to the SAVEPOINT if it is still open (a
                # runner that already committed internally closes it, in
                # which case there is nothing uncommitted left to discard).
                if savepoint.is_active:
                    savepoint.rollback()
                # A flush/commit failure can additionally leave the whole
                # session pending-rollback at the SQLAlchemy level even
                # after the SAVEPOINT itself is gone; only then does the
                # outer transaction need releasing too, and by that point
                # nothing from this job was ever durably committed, so nothing
                # legitimate is lost — only this job's own uncommitted work.
                try:
                    db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
                except SQLAlchemyError:
                    db.rollback()
                failed += 1
                error = {"job_id": job_id, "city_id": city_id, "source": source, "error": str(exc)[:500]}
                errors.append(error)
                failed_job = _mark_worker_exception(db, job_id=job_id, error=str(exc), expected_claimed_by=worker_id)
                claimed_jobs.append({
                    "job_id": job_id,
                    "terminal_status": str(failed_job.status if failed_job else "failed"),
                    "claimed_by": failed_job.claimed_by if failed_job is not None else None,
                    "expected_claimed_by": worker_id,
                    "finished_at": failed_job.finished_at.isoformat() if failed_job is not None and failed_job.finished_at else None,
                })
                _log_worker_decision(
                    db,
                    event="worker_job_failed",
                    actor_id=actor_id,
                    level="error",
                    message=f"Import worker failed job #{job_id}: {str(exc)[:300]}",
                    job=failed_job,
                    details=error,
                )
                db.commit()
                send_admin_alert(
                    title="Import worker job failed",
                    message=str(exc)[:1000],
                    level="error",
                    job_id=job_id,
                    details=error,
                )
        queue = import_queue_summary(db)
    return {
        "processed": processed,
        "failed": failed,
        "stalled_marked": stalled,
        "errors": errors,
        "queue": queue,
        "claimed_jobs": claimed_jobs,
    }


def _queued_seconds(job: CityAdminImportJob, *, now: datetime | None = None) -> int | None:
    if job.created_at is None:
        return None
    return max(0, int(((now or datetime.utcnow()) - job.created_at).total_seconds()))


def _log_worker_decision(
    db: Session,
    *,
    event: str,
    actor_id: str | None,
    message: str,
    job: CityAdminImportJob | None = None,
    level: str = "info",
    details: dict[str, object] | None = None,
) -> None:
    city_slug: str | None = None
    request_id: str | None = None
    payload = dict(details or {})
    payload["event"] = event
    if job is not None:
        request_id = str(job.id)
        payload.update({"job_id": int(job.id), "city_id": int(job.city_id), "source": job.source, "status": job.status})
        city = db.query(City).filter(City.id == job.city_id).first()
        city_slug = city.slug if city is not None else None
    write_system_log(
        db,
        level=level,
        module="import_worker",
        message=message,
        details=payload,
        city_slug=city_slug,
        request_id=request_id,
        actor_id=actor_id,
        commit=False,
    )


def _mark_worker_exception(db: Session, *, job_id: int, error: str, expected_claimed_by: str) -> CityAdminImportJob | None:
    # expected_claimed_by is required (this worker's own claim identity,
    # the same one passed to claim_queued_job for this exact job_id) —
    # finalize_import_job re-selects the row under FOR UPDATE and verifies BOTH
    # status=="running" AND claimed_by==expected_claimed_by before writing
    # anything. If the row already left "running" (e.g. a concurrent
    # stall-recovery sweep or admin cancel raced ahead of this exception
    # handler and was committed by a DIFFERENT connection — this is
    # exactly what happens when a runner's own atomic finalize attempt
    # lost that race and its InvalidJobTransitionError-equivalent
    # propagated here as the caught exception), result.ok is False and
    # none of the fields below are written — the row's real terminal
    # state (set by whoever actually holds the lock first) must not be
    # overwritten with this run's own late-arriving crash message.
    finished_at = datetime.utcnow()
    job_for_details = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job_for_details is None:
        return None
    details = dict(job_for_details.step_details or {})
    details["worker_exception"] = {"error": error[:1000], "failed_at": finished_at.isoformat()}
    result = finalize_import_job(
        db, job_id=job_id, new_status="failed", expected_claimed_by=expected_claimed_by, actor_id="import-worker",
        fields={
            "current_step": STEP_ERROR,
            "last_error": error[:2000],
            "failed_items": max(int(job_for_details.failed_items or 0), 1),
            "finished_at": finished_at,
            "updated_at": finished_at,
            "step_details": details,
        },
    )
    if result.ok:
        return result.job
    return db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()


def mark_stalled_import_jobs(db, *, actor_id: str = "import-worker", now: datetime | None = None) -> int:
    current = now or datetime.utcnow()
    # This batch SELECT (no FOR UPDATE) only needs to name candidates —
    # finalize_import_job below re-selects and re-locks each exact row
    # itself before writing anything, so two concurrent stall-sweeps (e.g.
    # a cron tick overlapping an admin's manual "mark stalled" click, or a
    # worker finishing normally in the same moment) can never both act on
    # the same row: whichever finalize_import_job call acquires the row's
    # lock first wins, and the other sees status is no longer "running"
    # and writes nothing.
    jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").all()
    candidates = [job for job in jobs if is_stalled(job, now=current)]
    alerts: list[dict[str, object]] = []
    marked = 0
    for candidate in candidates:
        job_id = int(candidate.id)
        city_id = int(candidate.city_id)
        last_error = candidate.last_error or "Import job stalled: no heartbeat before timeout"
        step_details = dict(candidate.step_details or {})
        step_details.update({"stalled_at": current.isoformat(), "stalled": True})
        # Administrative override — no expected_claimed_by — since this
        # sweep does not care who claimed the row, only whether it is
        # genuinely still running and unfinished by the time
        # finalize_import_job's own lock is acquired.
        result = finalize_import_job(
            db, job_id=job_id, new_status="stalled", actor_id=actor_id,
            fields={
                "finished_at": current,
                "last_error": last_error,
                "current_step": STEP_ERROR,
                "step_details": step_details,
                "updated_at": current,
            },
        )
        if not result.ok:
            # Someone else (a worker finishing normally, or a concurrent
            # sweep/admin action) already terminalized this row between the
            # batch SELECT above and this call — skip it, its real terminal
            # state must not be overwritten.
            continue
        job = result.job
        city = db.query(City).filter(City.id == city_id).first()
        city_slug = city.slug if city is not None else None
        if city is not None and city.launch_status == "importing":
            city.launch_status = "import_failed"
            city.is_active = False
        write_system_log(
            db,
            level="error",
            module="import_worker",
            message=f"Import worker marked job #{job.id} as stalled: {job.last_error}",
            details={
                "event": "worker_job_stalled",
                "job_id": int(job.id),
                "city_id": int(job.city_id),
                "source": job.source,
                "previous_status": "running",
                "new_status": "stalled",
                "last_error": job.last_error,
            },
            city_slug=city_slug,
            request_id=str(job.id),
            actor_id=actor_id,
            commit=False,
        )
        try:
            refresh_import_job_snapshot(db, city_id=city_id, source="stalled_job_recovery")
        except Exception:
            pass
        alerts.append({"job_id": int(job.id), "city_slug": city_slug, "source": job.source, "last_error": job.last_error})
        marked += 1
    if marked:
        db.commit()
        for alert in alerts:
            send_admin_alert(
                title="Import job stalled",
                message="Import job stopped sending heartbeat and was marked as stalled.",
                level="error",
                city_slug=str(alert.get("city_slug") or "") or None,
                job_id=int(alert["job_id"]),
                details=alert,
            )
    return marked


def import_queue_summary(db) -> dict[str, Any]:
    jobs = db.query(CityAdminImportJob).all()
    queued_jobs = [job for job in jobs if job.status == "queued"]
    running_jobs = [job for job in jobs if job.status == "running"]
    active_jobs = queued_jobs + running_jobs
    now = datetime.utcnow()
    oldest_queued_seconds = None
    if queued_jobs:
        oldest = min((job.created_at for job in queued_jobs if job.created_at), default=None)
        if oldest is not None:
            oldest_queued_seconds = int((now - oldest).total_seconds())
    next_jobs = sorted(queued_jobs, key=lambda item: (item.created_at or datetime.min, item.id))[:10]
    return {
        "total": len(jobs),
        "active_total": len(active_jobs),
        "by_status": dict(Counter(str(job.status or "unknown") for job in active_jobs)),
        "by_source": dict(Counter(str(job.source or "unknown") for job in active_jobs)),
        "queued": len(queued_jobs),
        "running": len(running_jobs),
        "stalled_running": sum(1 for job in running_jobs if is_stalled(job, now=now)),
        "oldest_queued_seconds": oldest_queued_seconds,
        "next_job_ids": [job.id for job in next_jobs],
        "running_job_ids": [job.id for job in running_jobs],
    }
