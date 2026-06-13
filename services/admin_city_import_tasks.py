"""Фоновый запуск import jobs."""

from __future__ import annotations

from db.session import SessionLocal
from models.city import City
from services.admin_city_import_job_service import run_city_import_job, run_enrichment_only_job


def run_import_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_city_import_job(db, city_id=city_id, actor_id=actor_id)


def run_enrichment_job_background(city_id: int, *, actor_id: str) -> None:
    with SessionLocal() as db:
        run_enrichment_only_job(db, city_id=city_id, actor_id=actor_id)


def run_all_cities_enrichment_background(*, actor_id: str) -> None:
    """Sequentially run enrichment-only pipeline for every city in production DB.

    FastAPI BackgroundTasks runs inside the backend process, so this endpoint is intended as an
    admin-triggered operational action. Each city gets its own DB session to avoid a single failed
    transaction poisoning the whole batch.
    """
    with SessionLocal() as db:
        city_ids = [city.id for city in db.query(City).order_by(City.slug.asc()).all()]

    for city_id in city_ids:
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
