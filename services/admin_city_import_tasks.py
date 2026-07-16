"""Фоновый запуск import jobs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
    InvalidJobTransitionError,
    _transition,
    run_address_enrichment_job,
    run_city_import_job,
    run_enrichment_only_job,
    run_photo_enrichment_job,
    run_snapshot_refresh_job,
)
from services.import_pipeline.progress import is_stalled, set_step
from services.import_pipeline.steps import STEP_ERROR
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.import_worker_thresholds import effective_thresholds
from services.system_log_service import write_system_log

HEAVY_IMPORT_SOURCES = {SOURCE_FULL_IMPORT, SOURCE_ENRICHMENT_ONLY}


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


def run_import_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_city_import_job(db, city_id=city_id, actor_id=actor_id)


def run_enrichment_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


def run_all_cities_enrichment_background(*, actor_id: str) -> None:
    with SessionLocal() as db:
        city_ids = [city.id for city in db.query(City).order_by(City.slug.asc()).all()]
    for city_id in city_ids:
        with SessionLocal() as db:
            run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


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
        jobs = query.with_for_update(skip_locked=True).limit(limit).all()
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
            # The claim decision is committed durably BEFORE any SAVEPOINT
            # begins: it is a truthful record that the worker claimed this
            # job, and must survive even if the job's own work later fails
            # and is rolled back.
            _log_worker_decision(
                db,
                event="worker_job_claimed",
                actor_id=actor_id,
                message=f"Import worker claiming job #{job_id} (city_id={city_id}, source={source})",
                job=job,
                details={"limit": limit, "queued_seconds": _queued_seconds(job), "stalled_marked": stalled},
            )
            db.commit()
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
                if source == SOURCE_ENRICHMENT_ONLY:
                    run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_SNAPSHOT_REFRESH:
                    run_snapshot_refresh_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_ADDRESS_ENRICHMENT:
                    run_address_enrichment_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                elif source == SOURCE_PHOTO_ENRICHMENT:
                    run_photo_enrichment_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                else:
                    run_city_import_job(db, city_id=city_id, actor_id=actor_id, job_id=job_id)
                processed += 1
                claimed_jobs.append({"job_id": job_id, "terminal_status": str(job.status)})
                _log_worker_decision(
                    db,
                    event="worker_job_finished",
                    actor_id=actor_id,
                    message=f"Import worker finished job #{job_id}",
                    job=job,
                    details={"final_status": job.status, "source": source},
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
                failed_job = _mark_worker_exception(db, job_id=job_id, error=str(exc))
                claimed_jobs.append({"job_id": job_id, "terminal_status": str(failed_job.status if failed_job else "failed")})
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


def _mark_worker_exception(db: Session, *, job_id: int, error: str) -> CityAdminImportJob | None:
    job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job is None:
        return None
    try:
        _transition(db, job, "failed", actor_id="import-worker")
    except InvalidJobTransitionError:
        pass
    job.current_step = STEP_ERROR
    job.last_error = error[:2000]
    job.failed_items = max(int(job.failed_items or 0), 1)
    job.finished_at = datetime.utcnow()
    job.updated_at = job.finished_at
    details = dict(job.step_details or {})
    details["worker_exception"] = {"error": error[:1000], "failed_at": job.finished_at.isoformat()}
    job.step_details = details
    return job


def mark_stalled_import_jobs(db, *, actor_id: str = "import-worker", now: datetime | None = None) -> int:
    current = now or datetime.utcnow()
    jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").all()
    stalled = [job for job in jobs if is_stalled(job, now=current)]
    alerts: list[dict[str, object]] = []
    for job in stalled:
        city = db.query(City).filter(City.id == job.city_id).first()
        previous_status = job.status
        _transition(db, job, "stalled", actor_id=actor_id)
        job.finished_at = current
        job.last_error = job.last_error or "Import job stalled: no heartbeat before timeout"
        set_step(job, STEP_ERROR, detail={"stalled_at": current.isoformat(), "stalled": True})
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
                "previous_status": previous_status,
                "new_status": "stalled",
                "last_error": job.last_error,
            },
            city_slug=city_slug,
            request_id=str(job.id),
            actor_id=actor_id,
            commit=False,
        )
        try:
            refresh_import_job_snapshot(db, city_id=int(job.city_id), source="stalled_job_recovery")
        except Exception:
            pass
        alerts.append({"job_id": int(job.id), "city_slug": city_slug, "source": job.source, "last_error": job.last_error})
    if stalled:
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
    return len(stalled)


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
