"""Фоновый запуск import jobs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import (
    SOURCE_ENRICHMENT_ONLY,
    run_city_import_job,
    run_enrichment_only_job,
)
from services.import_pipeline.progress import is_stalled


def run_import_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_city_import_job(db, city_id=city_id, actor_id=actor_id)


def run_enrichment_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


def run_all_cities_enrichment_background(*, actor_id: str) -> None:
    """Sequentially run enrichment-only pipeline for every city in production DB.

    Kept for compatibility with older callers. New admin HTTP actions enqueue DB jobs and let the
    import-worker process them outside the FastAPI request lifecycle.
    """
    with SessionLocal() as db:
        city_ids = [city.id for city in db.query(City).order_by(City.slug.asc()).all()]

    for city_id in city_ids:
        with SessionLocal() as db:
            run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


def run_queued_import_jobs(*, actor_id: str = "import-worker", limit: int = 1) -> dict[str, Any]:
    limit = max(1, int(limit or 1))
    with SessionLocal() as db:
        jobs = (
            db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.status == "queued")
            .order_by(CityAdminImportJob.created_at.asc(), CityAdminImportJob.id.asc())
            .limit(limit)
            .all()
        )
        work = [(int(job.id), int(job.city_id), str(job.source or "")) for job in jobs]

    processed = 0
    failed = 0
    errors: list[dict[str, object]] = []
    for job_id, city_id, source in work:
        try:
            with SessionLocal() as db:
                if source == SOURCE_ENRICHMENT_ONLY:
                    run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)
                else:
                    run_city_import_job(db, city_id=city_id, actor_id=actor_id)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"job_id": job_id, "city_id": city_id, "source": source, "error": str(exc)[:500]})
    with SessionLocal() as db:
        queue = import_queue_summary(db)
    return {"processed": processed, "failed": failed, "errors": errors, "queue": queue}


def import_queue_summary(db) -> dict[str, Any]:
    jobs = db.query(CityAdminImportJob).all()
    by_status = Counter(str(job.status or "unknown") for job in jobs)
    by_source = Counter(str(job.source or "unknown") for job in jobs)
    queued_jobs = [job for job in jobs if job.status == "queued"]
    running_jobs = [job for job in jobs if job.status == "running"]
    now = datetime.utcnow()
    oldest_queued_seconds = None
    if queued_jobs:
        oldest = min((job.created_at for job in queued_jobs if job.created_at), default=None)
        if oldest is not None:
            oldest_queued_seconds = int((now - oldest).total_seconds())
    return {
        "total": len(jobs),
        "by_status": dict(by_status),
        "by_source": dict(by_source),
        "queued": len(queued_jobs),
        "running": len(running_jobs),
        "stalled_running": sum(1 for job in running_jobs if is_stalled(job, now=now)),
        "oldest_queued_seconds": oldest_queued_seconds,
        "next_job_ids": [job.id for job in sorted(queued_jobs, key=lambda item: (item.created_at, item.id))[:10]],
    }