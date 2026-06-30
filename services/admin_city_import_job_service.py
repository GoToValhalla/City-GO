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
from services.admin_city_import_log import log_import_event
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
from services.import_pipeline.runner import run_enrichment_pipeline
from services.import_pipeline.steps import STEP_CANCELLED, STEP_ERROR, STEP_QUEUED
from services.import_pipeline_foundation import run_foundation_pipeline
from services.admin_import_job_change_service import CHANGE_TYPES, record_place_changes
from services.admin_city_import_job_payload import SNAPSHOT_KEY

SOURCE_FULL_IMPORT = "admin_city_import"
SOURCE_ENRICHMENT_ONLY = "admin_city_enrichment"
SOURCE_SNAPSHOT_REFRESH = "admin_snapshot_refresh"
SOURCE_ADDRESS_ENRICHMENT = "admin_address_enrichment"
SOURCE_PHOTO_ENRICHMENT = "admin_photo_enrichment"
ADDRESS_LIMIT = 5000
IMAGE_LIMIT = 2000


def queue_city_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    return _queue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def queue_city_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    return queue_city_import_job(db, city_id=city_id, actor_id=actor_id)


def queue_city_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    return _queue_job(db, city=city, source=SOURCE_SNAPSHOT_REFRESH, actor_id=actor_id)


def queue_city_address_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    return _queue_job(db, city=city, source=SOURCE_ADDRESS_ENRICHMENT, actor_id=actor_id)


def queue_city_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    return _queue_job(db, city=city, source=SOURCE_PHOTO_ENRICHMENT, actor_id=actor_id)


def ensure_import_job(db: Session, *, city_id: int) -> CityAdminImportJob:
    from services.admin_city_import_job_payload import _latest_job
    return _latest_job(db, city_id) or queue_city_import_job(db, city_id=city_id)


def _queue_job(db: Session, *, city: City, source: str, actor_id: str | None) -> CityAdminImportJob:
    from services.admin_city_import_job_payload import _latest_job
    job = _latest_job(db, city.id)
    if job is not None and job.status in {"queued", "running"}:
        raise ValueError("Pipeline уже выполняется")
    scopes = db.query(CityImportScope).filter_by(city_id=city.id, enabled=True).count()
    if job is None:
        job = CityAdminImportJob(city_id=city.id); db.add(job); db.flush()
    job.status = "queued"; job.source = source; job.scopes_total = scopes; job.current_step = STEP_QUEUED
    job.places_found = 0; job.places_saved = 0; job.scopes_succeeded = 0; job.total_items = 0; job.processed_items = 0; job.successful_items = 0; job.failed_items = 0
    job.step_details = {"city_state_before_import": {"launch_status": city.launch_status, "is_active": bool(city.is_active)}}
    job.started_at = None; job.finished_at = None; job.last_error = None; job.cancelled_at = None; job.updated_at = datetime.utcnow()
    log_import_event(db, event="import_job_created", city_slug=city.slug, actor_id=actor_id, message=f"Создана задача {source} #{job.id}", details={"job_id": job.id, "scopes_total": scopes, "source": source})
    return job


def run_city_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running": raise ValueError("Импорт уже выполняется")
    if job.current_step == STEP_CANCELLED: raise ValueError("Задача отменена. Создайте новую через повтор.")
    job.status = "running"; job.source = SOURCE_FULL_IMPORT; job.started_at = datetime.utcnow(); job.finished_at = None; job.last_error = None; job.scopes_total = db.query(CityImportScope).filter_by(city_id=city_id, enabled=True).count()
    log_import_event(db, event="import_job_started", city_slug=city.slug, actor_id=actor_id, message=f"Старт полного pipeline #{job.id}", details={"job_id": job.id, "source": job.source}); db.commit()
    try:
        legacy = run_enrichment_pipeline(db, job=job, city=city, actor_id=actor_id, force=True, notify_completion=False); db.refresh(job); db.refresh(city)
        ids = [int(v) for v in legacy.get("changed_place_ids", [])]; warnings = list((job.step_details or {}).get("warnings") or []); saved = (job.places_found, job.places_saved, job.scopes_succeeded)
        job.status = "running"; job.finished_at = None; db.commit(); source = _foundation(db, city, job, actor_id, ids); source_status = job.status; job.places_found, job.places_saved, job.scopes_succeeded = saved
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}; places = db.query(Place).filter(Place.id.in_(ids)).order_by(Place.id).all() if ids else []; record_place_changes(db, job=job, places=places, since=job.started_at or datetime.utcnow())
        if source_status in {"partial_success", "success_with_warnings", "failed"} or int(source.get("failed") or 0) > 0: warnings.append({"step": "source_enrichment", "error": f"Ошибок этапов обогащения: {int(source.get('failed') or 0)}"})
        job.step_details = {**dict(job.step_details or {}), "warnings": warnings, "changed_place_ids": ids, "has_changes": bool(ids), "unified_pipeline": {"collection_and_legacy_enrichment": legacy, "source_enrichment": source, "readiness_score": readiness.get("readiness_score"), "completed": True}}
        job.status = "success_with_warnings" if warnings else "success"; job.finished_at = datetime.utcnow()
        if ids: city.launch_status = "review_required"; city.is_active = False
        city.last_import_at = job.finished_at; _refresh_snapshot_light(db, city=city, job=job, source="import_worker_finished")
        log_import_event(db, event="unified_import_pipeline_finished", city_slug=city.slug, actor_id=actor_id, message=f"Полный pipeline #{job.id}: {len(ids)} изменений", details={"job_id": job.id, "changed_places": len(ids), "warnings": warnings}); db.commit(); _alert(db, city, job, len(ids), readiness, warnings)
    except Exception as exc:
        db.rollback(); job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).first(); city = db.query(City).filter(City.id == city_id).first(); total = db.query(Place).filter(Place.city_id == city_id).count(); ids = [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])] if job else []
        if job: job.status = "partial_success" if total > 0 else "failed"; job.last_error = str(exc)[:2000]; job.finished_at = datetime.utcnow()
        if city is not None and ids: city.launch_status = "review_required"; city.is_active = False
        db.commit(); send_admin_alert(title="Import completed with warnings" if total > 0 else "Import pipeline failed", message=f"Pipeline прерван. Изменённых мест: {len(ids)}.", level="warning" if total > 0 else "error", city_slug=city.slug if city else None, job_id=int(job.id) if job else None, details={"status": job.status if job else "failed", "places_total": total, "changed_places": len(ids), "warnings": [{"step": "unified_pipeline", "error": str(exc)[:1000]}]})
    db.refresh(job); return job


def run_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id); job.status = "running"; job.source = SOURCE_SNAPSHOT_REFRESH; job.current_step = "snapshot_refresh"; job.started_at = datetime.utcnow(); db.commit()
    _refresh_snapshot_light(db, city=city, job=job, source="snapshot_refresh_job")
    job.status = "success"; job.finished_at = datetime.utcnow(); job.current_step = "snapshot_ready"; db.commit(); db.refresh(job); return job


def run_address_enrichment_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id); job.status = "running"; job.source = SOURCE_ADDRESS_ENRICHMENT; job.current_step = "finding_addresses"; job.started_at = datetime.utcnow(); db.commit()
    result = run_address_backfill(["--city", city.slug, "--limit", str(ADDRESS_LIMIT), "--apply"])
    job.step_details = {**dict(job.step_details or {}), "address_enrichment": result}; job.status = "success"; job.finished_at = datetime.utcnow(); job.current_step = "snapshot_refresh"; db.commit(); _refresh_snapshot_light(db, city=city, job=job, source="address_enrichment_finished"); db.refresh(job); return job


def run_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id); job.status = "running"; job.source = SOURCE_PHOTO_ENRICHMENT; job.current_step = "finding_images"; job.started_at = datetime.utcnow(); db.commit()
    result = run_image_enrich(["--city", city.slug, "--limit", str(IMAGE_LIMIT), "--apply"])
    job.step_details = {**dict(job.step_details or {}), "photo_enrichment": result}; job.status = "success"; job.finished_at = datetime.utcnow(); job.current_step = "snapshot_refresh"; db.commit(); _refresh_snapshot_light(db, city=city, job=job, source="photo_enrichment_finished"); db.refresh(job); return job


def _refresh_snapshot_light(db: Session, *, city: City, job: CityAdminImportJob, source: str) -> dict[str, object]:
    total = db.query(Place).filter(Place.city_id == city.id).count()
    published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
    without_address = db.query(Place).filter(Place.city_id == city.id, Place.address.is_(None)).count()
    without_photo = db.query(Place).filter(Place.city_id == city.id, Place.image_url.is_(None)).count()
    without_description = db.query(Place).filter(Place.city_id == city.id, Place.short_description.is_(None)).count()
    pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    def pct(missing: int) -> float: return round(((total - missing) / total) * 100, 1) if total else 0.0
    coverage = {"places_total": int(total), "places_published": int(published), "places_unpublished": max(int(total) - int(published), 0), "without_address": int(without_address), "without_photo": int(without_photo), "without_description": int(without_description), "address_coverage_pct": pct(int(without_address)), "photo_coverage_pct": pct(int(without_photo)), "description_coverage_pct": pct(int(without_description)), "pending_photos": int(pending_photos)}
    existing_changes = dict(job.step_details or {}).get("change_summary")
    changes = existing_changes if isinstance(existing_changes, dict) else {"job_id": job.id, "city_id": city.id, "city_slug": city.slug, **{key: 0 for key in CHANGE_TYPES}}
    changes = {**changes, "total_changes": sum(int(changes.get(key) or 0) for key in CHANGE_TYPES)}
    snapshot = {"version": 1, "source": source, "taken_at": datetime.utcnow().isoformat(), "city_id": city.id, "city_slug": city.slug, "job_id": job.id, "data_coverage": coverage, "change_summary": changes}
    details = dict(job.step_details or {}); details[SNAPSHOT_KEY] = snapshot; details["data_coverage"] = coverage; details["change_summary"] = changes
    job.step_details = details; job.updated_at = datetime.utcnow(); db.commit(); return snapshot


def _foundation(db, city, job, actor_id, ids):
    kwargs = {"db": db, "city": city, "job": job, "actor": actor_id}
    if "place_ids" in inspect.signature(run_foundation_pipeline).parameters: kwargs["place_ids"] = ids
    return run_foundation_pipeline(**kwargs)


def _alert(db, city, job, changed, readiness, warnings):
    total = db.query(Place).filter(Place.city_id == city.id).count(); send_admin_alert(title="Import completed with warnings" if warnings else "Import pipeline finished", message=f"{city.name}: {changed} мест обновлено и отправлено на подтверждение." if changed else f"{city.name}: изменений нет, публикация сохранена.", level="warning" if warnings else "info", city_slug=city.slug, job_id=int(job.id), details={"status": job.status, "source": job.source, "places_total": total, "changed_places": changed, "readiness": readiness, "warnings": warnings})


def reset_import_job_to_queued(db: Session, *, city_id: int) -> CityAdminImportJob:
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running": raise ValueError("Импорт уже выполняется")
    city = db.query(City).filter(City.id == city_id).first(); job.status = "queued"; job.current_step = STEP_QUEUED; job.source = SOURCE_FULL_IMPORT; job.last_error = None; job.step_details = {"city_state_before_import": {"launch_status": city.launch_status if city else None, "is_active": bool(city.is_active) if city else False}}; job.total_items = 0; job.processed_items = 0; job.successful_items = 0; job.failed_items = 0; job.started_at = None; job.finished_at = None; job.cancelled_at = None; job.retry_count = (job.retry_count or 0) + 1; db.commit(); db.refresh(job); return job


def run_enrichment_only_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None: raise ValueError("Город не найден")
    job = ensure_import_job(db, city_id=city_id)
    if job.status == "running": raise ValueError("Pipeline уже выполняется")
    job.status = "running"; job.source = SOURCE_ENRICHMENT_ONLY; job.started_at = datetime.utcnow(); job.finished_at = None; job.last_error = None; db.commit()
    try: run_enrichment_only_pipeline(db, job=job, city=city, actor_id=actor_id); db.refresh(job); _foundation(db, city, job, actor_id, [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])]); _refresh_snapshot_light(db, city=city, job=job, source="enrichment_only_finished")
    except Exception as exc:
        job.status = "failed"; job.current_step = STEP_ERROR; job.last_error = str(exc)[:2000]; job.failed_items = max(int(job.failed_items or 0), 1); job.finished_at = datetime.utcnow(); job.updated_at = job.finished_at
        details = dict(job.step_details or {}); details["worker_exception"] = {"error": str(exc)[:1000], "failed_at": job.finished_at.isoformat()}; job.step_details = details; db.commit(); raise
    db.refresh(job); return job


def cancel_import_job(db: Session, *, city_id: int, actor_id: str) -> CityAdminImportJob:
    job = ensure_import_job(db, city_id=city_id)
    if job.status != "running" and job.current_step not in {STEP_QUEUED, "queued"} and job.status in {"success", "failed"}: raise ValueError("Задача уже завершена")
    job.status = "cancelled"; job.current_step = STEP_CANCELLED; job.cancelled_at = datetime.utcnow(); job.finished_at = datetime.utcnow(); city = db.query(City).filter(City.id == city_id).first()
    if city: log_import_event(db, event="import_job_cancelled", city_slug=city.slug, actor_id=actor_id, message=f"Импорт #{job.id} отменён без изменения публикации города", details={"job_id": job.id, "source": job.source})
    db.commit(); db.refresh(job); return job
