"""Фоновый запуск import jobs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_job_service import (
    SOURCE_ADDRESS_ENRICHMENT,
    SOURCE_ENRICHMENT_ONLY,
    SOURCE_PHOTO_ENRICHMENT,
    SOURCE_SNAPSHOT_REFRESH,
    run_address_enrichment_job,
    run_city_import_job,
    run_enrichment_only_job,
    run_photo_enrichment_job,
    run_snapshot_refresh_job,
)
from services.import_pipeline.progress import is_stalled, set_step
from services.import_pipeline.steps import STEP_ERROR
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.system_log_service import write_system_log


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


def run_queued_import_jobs(*, actor_id: str = "import-worker", limit: int = 1) -> dict[str, Any]:
    limit = max(1, int(limit or 1))
    processed = 0
    failed = 0
    errors: list[dict[str, object]] = []
    with SessionLocal() as db:
        stalled = mark_stalled_import_jobs(db, actor_id=actor_id)
        jobs = (
            db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.status == "queued")
            .order_by(CityAdminImportJob.created_at.asc(), CityAdminImportJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )
        if not jobs:
            running_count = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").count()
            _log_worker_decision(
                db,
                event="worker_no_queued_jobs",
                actor_id=actor_id,
                message=f"Import worker found no queued jobs; active running jobs: {running_count}",
                details={"limit": limit, "running": running_count, "stalled_marked": stalled},
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
            try:
                _log_worker_decision(
                    db,
                    event="worker_job_claimed",
                    actor_id=actor_id,
                    message=f"Import worker claiming job #{job_id} (city_id={city_id}, source={source})",
                    job=job,
                    details={"limit": limit, "queued_seconds": _queued_seconds(job), "stalled_marked": stalled},
                )
                if source == SOURCE_ENRICHMENT_ONLY:
                    run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)
                elif source == SOURCE_SNAPSHOT_REFRESH:
                    run_snapshot_refresh_job(db, city_id=city_id, actor_id=actor_id)
                elif source == SOURCE_ADDRESS_ENRICHMENT:
                    run_address_enrichment_job(db, city_id=city_id, actor_id=actor_id)
                elif source == SOURCE_PHOTO_ENRICHMENT:
                    run_photo_enrichment_job(db, city_id=city_id, actor_id=actor_id)
                else:
                    run_city_import_job(db, city_id=city_id, actor_id=actor_id)
                processed += 1
                _log_worker_decision(
                    db,
                    event="worker_job_finished",
                    actor_id=actor_id,
                    message=f"Import worker finished job #{job_id}",
                    job=job,
                    details={"final_status": job.status, "source": source},
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, SQLAlchemyError):
                    db.rollback()
                failed += 1
                error = {"job_id": job_id, "city_id": city_id, "source": source, "error": str(exc)[:500]}
                errors.append(error)
                _mark_worker_exception(job_id=job_id, error=str(exc))
                _log_worker_decision(
                    db,
                    event="worker_job_failed",
                    actor_id=actor_id,
                    level="error",
                    message=f"Import worker failed job #{job_id}: {str(exc)[:300]}",
                    job=job,
                    details=error,
                )
                db.commit()
                send_admin_alert(title="Import worker job failed", message=str(exc)[:1000], level="error", job_id=job_id, details=error)
        queue = import_queue_summary(db)
    return {"processed": processed, "failed": failed, "stalled_marked": stalled, "errors": errors, "queue": queue}


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


def _mark_worker_exception(*, job_id: int, error: str) -> None:
    with SessionLocal() as db:
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        if job is None:
            return
        job.status = "failed"
        job.current_step = STEP_ERROR
        job.last_error = error[:2000]
        job.failed_items = max(int(job.failed_items or 0), 1)
        job.finished_at = datetime.utcnow()
        job.updated_at = job.finished_at
        details = dict(job.step_details or {})
        details["worker_exception"] = {"error": error[:1000], "failed_at": job.finished_at.isoformat()}
        job.step_details = details
        db.commit()


def mark_stalled_import_jobs(db, *, actor_id: str = "import-worker", now: datetime | None = None) -> int:
    current = now or datetime.utcnow()
    jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").all()
    stalled = [job for job in jobs if is_stalled(job, now=current)]
    alerts: list[dict[str, object]] = []
    for job in stalled:
        city = db.query(City).filter(City.id == job.city_id).first()
        job.status = "stalled"
        job.finished_at = current
        job.last_error = job.last_error or "Import job stalled: no heartbeat before timeout"
        set_step(job, STEP_ERROR, detail={"stalled_at": current.isoformat(), "stalled": True})
        city_slug = city.slug if city is not None else None
        if city is not None and city.launch_status == "importing":
            city.launch_status = "import_failed"
            city.is_active = False
        try:
            refresh_import_job_snapshot(db, city_id=int(job.city_id), source="stalled_job_recovery")
        except Exception:
            pass
        alerts.append({"job_id": int(job.id), "city_slug": city_slug, "source": job.source, "last_error": job.last_error})
    if stalled:
        db.commit()
        for alert in alerts:
            send_admin_alert(title="Import job stalled", message="Import job stopped sending heartbeat and was marked as stalled.", level="error", city_slug=str(alert.get("city_slug") or "") or None, job_id=int(alert["job_id"]), details=alert)
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
    }
