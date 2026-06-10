"""Очередь и выполнение admin city import jobs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.admin_city_import_log import log_import_event
from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
from services.import_pipeline.runner import run_enrichment_pipeline
from services.import_pipeline.steps import STEP_CANCELLED, STEP_QUEUED


def queue_city_import_job(db: Session, *, city_id: int) -> CityAdminImportJob:
    scopes = db.query(CityImportScope).filter_by(city_id=city_id, enabled=True).count()
    job = CityAdminImportJob(city_id=city_id, status="queued", scopes_total=scopes, current_step=STEP_QUEUED)
    db.add(job)
    db.flush()
    city = db.query(City).filter(City.id == city_id).first()
    if city is not None:
        city.launch_status = "importing"
        log_import_event(db, event="import_job_created", city_slug=city.slug, actor_id=None,
                         message=f"Создана задача импорта #{job.id}", details={"job_id": job.id, "scopes_total": scopes})
    return job


def ensure_import_job(db: Session, *, city_id: int) -> CityAdminImportJob:
    from services.admin_city_import_job_payload import _latest_job

    job = _latest_job(db, city_id)
    return job if job is not None else queue_city_import_job(db, city_id=city_id)


def run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running":
        raise ValueError("Импорт уже выполняется")
    if job.current_step == STEP_CANCELLED:
        raise ValueError("Задача отменена. Создайте новую через повтор.")
    scopes = db.query(CityImportScope).filter_by(city_id=city_id, enabled=True).count()
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    job.scopes_total = scopes
    city.launch_status = "importing"
    log_import_event(db, event="import_job_started", city_slug=city.slug, actor_id=actor_id,
                     message=f"Старт pipeline #{job.id}", details={"job_id": job.id})
    db.commit()
    try:
        run_enrichment_pipeline(db, job=job, city=city, actor_id=actor_id, force=True)
    except Exception as exc:  # noqa: BLE001
        db.commit()
        db.refresh(job)
        if job.status != "failed":
            job.status = "failed"
            job.last_error = str(exc)[:2000]
            job.finished_at = datetime.utcnow()
            city.launch_status = "import_failed"
            db.commit()
    db.refresh(job)
    return job


def reset_import_job_to_queued(db: Session, *, city_id: int) -> CityAdminImportJob:
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running":
        raise ValueError("Импорт уже выполняется")
    job.status = "queued"
    job.current_step = STEP_QUEUED
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    job.cancelled_at = None
    job.retry_count = (job.retry_count or 0) + 1
    db.commit()
    db.refresh(job)
    return job


def run_enrichment_only_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running":
        raise ValueError("Pipeline уже выполняется")
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    db.commit()
    try:
        run_enrichment_only_pipeline(db, job=job, city=city, actor_id=actor_id)
    except Exception:
        db.commit()
        db.refresh(job)
    db.refresh(job)
    return job


def cancel_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    job = ensure_import_job(db, city_id=city_id)
    if job.status != "running" and job.current_step not in {STEP_QUEUED, "queued"}:
        if job.status in {"success", "failed"}:
            raise ValueError("Задача уже завершена")
    job.status = "cancelled"
    job.current_step = STEP_CANCELLED
    job.cancelled_at = datetime.utcnow()
    job.finished_at = datetime.utcnow()
    city = db.query(City).filter(City.id == city_id).first()
    if city is not None:
        city.launch_status = "import_failed"
        log_import_event(db, event="import_job_cancelled", city_slug=city.slug, actor_id=actor_id,
                         message=f"Импорт #{job.id} отменён", details={"job_id": job.id})
    db.commit()
    db.refresh(job)
    return job
