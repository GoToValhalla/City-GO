"""Очередь и выполнение admin city import jobs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from models.place import Place
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
from services.import_pipeline.runner import run_enrichment_pipeline
from services.import_pipeline.steps import STEP_CANCELLED, STEP_QUEUED
from services.import_pipeline_foundation import run_foundation_pipeline

SOURCE_FULL_IMPORT = "admin_city_import"
SOURCE_ENRICHMENT_ONLY = "admin_city_enrichment"


def queue_city_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _queue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def queue_city_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    """Compatibility alias: every new admin run uses the complete collection pipeline."""
    return queue_city_import_job(db, city_id=city_id, actor_id=actor_id)


def ensure_import_job(db: Session, *, city_id: int) -> CityAdminImportJob:
    from services.admin_city_import_job_payload import _latest_job

    job = _latest_job(db, city_id)
    return job if job is not None else queue_city_import_job(db, city_id=city_id)


def _queue_job(db: Session, *, city: City, source: str, actor_id: str | None) -> CityAdminImportJob:
    from services.admin_city_import_job_payload import _latest_job

    job = _latest_job(db, city.id)
    if job is not None and job.status == "running":
        raise ValueError("Pipeline уже выполняется")
    scopes = db.query(CityImportScope).filter_by(city_id=city.id, enabled=True).count()
    if job is None:
        job = CityAdminImportJob(city_id=city.id)
        db.add(job)
        db.flush()
    job.status = "queued"
    job.source = source
    job.scopes_total = scopes
    job.current_step = STEP_QUEUED
    job.places_found = 0
    job.places_saved = 0
    job.scopes_succeeded = 0
    job.total_items = 0
    job.processed_items = 0
    job.successful_items = 0
    job.failed_items = 0
    job.step_details = {}
    job.started_at = None
    job.finished_at = None
    job.last_error = None
    job.cancelled_at = None
    job.updated_at = datetime.utcnow()
    if source == SOURCE_FULL_IMPORT:
        city.launch_status = "importing"
        city.is_active = False
        message = f"Создана задача полного сбора и обогащения #{job.id}"
        event = "import_job_created"
    else:
        message = f"Создана задача обогащения #{job.id}"
        event = "enrichment_job_created"
    log_import_event(
        db,
        event=event,
        city_slug=city.slug,
        actor_id=actor_id,
        message=message,
        details={"job_id": job.id, "scopes_total": scopes, "source": source},
    )
    return job


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
    job.source = SOURCE_FULL_IMPORT
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    job.scopes_total = scopes
    city.launch_status = "importing"
    log_import_event(
        db,
        event="import_job_started",
        city_slug=city.slug,
        actor_id=actor_id,
        message=f"Старт полного pipeline #{job.id}",
        details={"job_id": job.id, "source": job.source},
    )
    db.commit()
    try:
        legacy_results = run_enrichment_pipeline(
            db,
            job=job,
            city=city,
            actor_id=actor_id,
            force=True,
            notify_completion=False,
        )
        db.refresh(job)
        db.refresh(city)
        collection_counters = {
            "places_found": job.places_found,
            "places_saved": job.places_saved,
            "scopes_succeeded": job.scopes_succeeded,
        }
        legacy_warnings = list((job.step_details or {}).get("warnings") or [])

        # The first stage may finish with warnings, but the job is not complete
        # until normalization, quality and publication decisions have run.
        job.status = "running"
        job.finished_at = None
        city.launch_status = "importing"
        db.commit()

        source_counters = run_foundation_pipeline(db, city=city, job=job, actor=actor_id)
        source_status = job.status
        job.places_found = collection_counters["places_found"]
        job.places_saved = collection_counters["places_saved"]
        job.scopes_succeeded = collection_counters["scopes_succeeded"]
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}
        foundation_warnings = []
        if source_status in {"partial_success", "success_with_warnings", "failed"} or int(source_counters.get("failed") or 0) > 0:
            foundation_warnings.append({
                "step": "source_enrichment",
                "error": f"Ошибок этапов обогащения: {int(source_counters.get('failed') or 0)}",
            })
        all_warnings = [*legacy_warnings, *foundation_warnings]
        job.step_details = {
            **dict(job.step_details or {}),
            "warnings": all_warnings,
            "unified_pipeline": {
                "collection_and_legacy_enrichment": legacy_results,
                "source_enrichment": source_counters,
                "readiness_score": readiness.get("readiness_score"),
                "completed": True,
            },
        }
        job.status = "success_with_warnings" if all_warnings else "success"
        job.finished_at = datetime.utcnow()
        city.launch_status = "review_required"
        city.is_active = False
        city.last_import_at = job.finished_at
        log_import_event(
            db,
            event="unified_import_pipeline_finished",
            city_slug=city.slug,
            actor_id=actor_id,
            message=f"Полный сбор и обогащение #{job.id} завершены",
            details={
                "job_id": job.id,
                "source_enrichment": source_counters,
                "readiness": readiness,
                "warnings": all_warnings,
            },
        )
        db.commit()
        send_admin_alert(
            title="Import completed with warnings" if all_warnings else "Import pipeline finished",
            message=(
                "Полный импорт завершён, но некоторые этапы требуют внимания."
                if all_warnings
                else f"{city.name} готов к проверке. Мест собрано: {db.query(Place).filter(Place.city_id == city.id).count()}."
            ),
            level="warning" if all_warnings else "info",
            city_slug=city.slug,
            job_id=int(job.id),
            details={
                "status": job.status,
                "source": job.source,
                "places_total": db.query(Place).filter(Place.city_id == city.id).count(),
                "readiness": readiness,
                "warnings": all_warnings,
            },
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).first()
        city = db.query(City).filter(City.id == city_id).first()
        places_total = db.query(Place).filter(Place.city_id == city_id).count()
        if job is not None:
            job.status = "partial_success" if places_total > 0 else "failed"
            job.last_error = str(exc)[:2000]
            job.finished_at = datetime.utcnow()
        if city is not None:
            city.launch_status = "review_required" if places_total > 0 else "import_failed"
            city.is_active = False
        db.commit()
        send_admin_alert(
            title="Import completed with warnings" if places_total > 0 else "Import pipeline failed",
            message=(
                "Pipeline прерван после сохранения мест. Требуется повтор или ручная проверка."
                if places_total > 0
                else "Импорт завершился ошибкой до сохранения мест."
            ),
            level="warning" if places_total > 0 else "error",
            city_slug=city.slug if city is not None else None,
            job_id=int(job.id) if job is not None else None,
            details={
                "status": job.status if job is not None else "failed",
                "source": job.source if job is not None else SOURCE_FULL_IMPORT,
                "places_total": places_total,
                "warnings": [{"step": "unified_pipeline", "error": str(exc)[:1000]}],
            },
        )
    db.refresh(job)
    return job


def reset_import_job_to_queued(db: Session, *, city_id: int) -> CityAdminImportJob:
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running":
        raise ValueError("Импорт уже выполняется")
    job.status = "queued"
    job.current_step = STEP_QUEUED
    job.source = SOURCE_FULL_IMPORT
    job.last_error = None
    job.step_details = {}
    job.total_items = 0
    job.processed_items = 0
    job.successful_items = 0
    job.failed_items = 0
    job.started_at = None
    job.finished_at = None
    job.cancelled_at = None
    job.retry_count = (job.retry_count or 0) + 1
    db.commit()
    db.refresh(job)
    return job


def run_enrichment_only_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    """Process old queued enrichment jobs without losing backward compatibility."""
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running":
        raise ValueError("Pipeline уже выполняется")
    job.status = "running"
    job.source = SOURCE_ENRICHMENT_ONLY
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    db.commit()
    try:
        run_enrichment_only_pipeline(db, job=job, city=city, actor_id=actor_id)
        db.refresh(job)
        run_foundation_pipeline(db, city=city, job=job, actor=actor_id)
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
        log_import_event(
            db,
            event="import_job_cancelled",
            city_slug=city.slug,
            actor_id=actor_id,
            message=f"Импорт #{job.id} отменён",
            details={"job_id": job.id, "source": job.source},
        )
    db.commit()
    db.refresh(job)
    return job
