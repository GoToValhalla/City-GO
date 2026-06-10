"""Фоновый запуск import jobs."""

from __future__ import annotations

from db.session import SessionLocal
from services.admin_city_import_job_service import run_city_import_job, run_enrichment_only_job


def run_import_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_city_import_job(db, city_id=city_id, actor_id=actor_id)


def run_enrichment_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


def run_queued_import_jobs(*, actor_id: str = "import-cron", limit: int = 3) -> int:
    from models.city_admin_import_job import CityAdminImportJob

    with SessionLocal() as db:
        jobs = (
            db.query(CityAdminImportJob)
            .filter(CityAdminImportJob.status == "queued")
            .order_by(CityAdminImportJob.created_at.asc())
            .limit(limit)
            .all()
        )
        city_ids = [job.city_id for job in jobs]
    processed = 0
    for city_id in city_ids:
        with SessionLocal() as db:
            run_city_import_job(db, city_id=city_id, actor_id=actor_id)
        processed += 1
    return processed
