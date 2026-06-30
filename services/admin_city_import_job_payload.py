"""Payload import jobs для admin API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_import_job_change_service import CHANGE_TYPES, import_job_changes_summary
from services.import_pipeline.progress import is_stalled, step_label
from services.import_pipeline.steps import STEP_QUEUED, STEP_READY_FOR_REVIEW, TERMINAL_STEPS

PUBLISHABLE_CITY_STATUSES = {"review_required", "imported", "success", "success_with_warnings", "partial_success", "import_failed", "unpublished"}
FAILED_IMPORT_STATUSES = {"failed", "stalled", "import_failed"}
REVIEWABLE_IMPORT_STATUSES = {"success", "success_with_warnings", "partial_success", "imported"}
REVIEWABLE_CITY_STATUSES = {"review_required", "imported"}
PIPELINE_MODE = "legacy_osm_plus_foundation"
PIPELINE_MODE_LABEL = "OSM сбор + foundation quality layer"


def _latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city_id).order_by(CityAdminImportJob.created_at.desc()).first()


def _is_published(city: City) -> bool:
    return city.launch_status == "published" and bool(city.is_active)


def recover_failed_import_with_places(db: Session, city: City, *, places_total: int | None = None, job: CityAdminImportJob | None = None, actor_id: str = "admin-panel-read") -> bool:
    if _is_published(city):
        return False
    total = places_total if places_total is not None else db.query(Place).filter(Place.city_id == city.id).count()
    if total <= 0:
        return False
    job = job or _latest_job(db, city.id)
    if job is None:
        return False
    if city.launch_status != "import_failed" and str(job.status or "") not in FAILED_IMPORT_STATUSES:
        return False
    if city.launch_status == "review_required" and str(job.status or "") == "partial_success":
        return False
    details = dict(job.step_details or {})
    details["failed_import_recovery"] = {"actor_id": actor_id, "reason": "failed_import_has_saved_places", "places_total": int(total), "previous_status": job.status, "previous_launch_status": city.launch_status, "last_error": job.last_error}
    job.step_details = details
    job.status = "partial_success"
    job.current_step = STEP_READY_FOR_REVIEW
    _sync_reviewable_job_counts(job, int(total))
    city.launch_status = "review_required"
    city.is_active = False
    db.commit()
    db.refresh(city)
    db.refresh(job)
    return True


def normalize_reviewable_import_state(db: Session, city: City, job: CityAdminImportJob | None, places_total: int, *, actor_id: str = "admin-panel-read") -> bool:
    if job is None or _is_published(city):
        return False
    status = str(job.status or "")
    is_reviewable = city.launch_status in REVIEWABLE_CITY_STATUSES or job.current_step == STEP_READY_FOR_REVIEW or (status in REVIEWABLE_IMPORT_STATUSES and city.launch_status not in {"draft", "importing", "import_failed"})
    if not is_reviewable:
        return False
    if places_total > 0:
        before = (job.total_items, job.processed_items, job.successful_items, job.places_found, job.places_saved)
        _sync_reviewable_job_counts(job, int(places_total))
        after = (job.total_items, job.processed_items, job.successful_items, job.places_found, job.places_saved)
        if before == after:
            return False
        details = dict(job.step_details or {})
        details["reviewable_count_sync"] = {"actor_id": actor_id, "reason": "reviewable_import_has_saved_places", "places_total": int(places_total)}
        job.step_details = details
        db.commit()
        db.refresh(job)
        return True
    reported_places = max(int(job.places_found or 0), int(job.places_saved or 0))
    if reported_places > 0:
        details = dict(job.step_details or {})
        details["place_count_mismatch"] = {"actor_id": actor_id, "reason": "import_reported_places_missing_from_database", "reported_places": reported_places, "places_total": 0}
        job.step_details = details
        db.commit()
        db.refresh(job)
        return True
    details = dict(job.step_details or {})
    details["empty_review_recovery"] = {"actor_id": actor_id, "reason": "reviewable_import_without_saved_places", "previous_status": job.status, "previous_launch_status": city.launch_status, "previous_step": job.current_step}
    job.step_details = details
    job.status = "failed"
    job.current_step = "error"
    job.last_error = job.last_error or "Город был готов к проверке, но сохраненных мест нет. Повторите импорт."
    job.total_items = 0
    job.processed_items = 0
    job.successful_items = 0
    job.places_found = 0
    job.places_saved = 0
    city.launch_status = "import_failed"
    city.is_active = False
    db.commit()
    db.refresh(city)
    db.refresh(job)
    return True


def _sync_reviewable_job_counts(job: CityAdminImportJob, places_total: int) -> None:
    job.total_items = max(int(job.total_items or 0), places_total)
    job.processed_items = max(int(job.processed_items or 0), places_total)
    job.successful_items = max(int(job.successful_items or 0), places_total)
    job.places_found = max(int(job.places_found or 0), places_total)
    job.places_saved = max(int(job.places_saved or 0), places_total)


def build_import_job_payload(db: Session, city: City) -> dict[str, object]:
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    recover_failed_import_with_places(db, city, places_total=places_total)
    job = _latest_job(db, city.id)
    if normalize_reviewable_import_state(db, city, job, places_total):
        job = _latest_job(db, city.id)
    places_published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
    pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    city_published = _is_published(city)
    raw_status = job.status if job is not None else city.launch_status
    raw_step = job.current_step if job is not None else STEP_QUEUED
    status = "published" if city_published else raw_status
    current_step = "published" if city_published else raw_step
    details = _admin_step_details(db, city=city, job=job, places_total=int(places_total), places_published=int(places_published), pending_photos=int(pending_photos))
    return {
        "id": f"city-import-{city.id}",
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "status": status,
        "launch_status": city.launch_status,
        "is_city_active": bool(city.is_active),
        "current_step": current_step,
        "current_step_label": "Опубликован" if city_published else step_label(current_step),
        "source": job.source if job is not None else "admin_city_import",
        "places_total": places_total,
        "places_published": places_published,
        "places_unpublished": max(places_total - places_published, 0),
        "pending_photos": pending_photos,
        "next_step": _import_next_step(current_step, status, city.launch_status),
        "job_id": job.id if job is not None else None,
        "scopes_total": job.scopes_total if job is not None else 0,
        "scopes_succeeded": job.scopes_succeeded if job is not None else 0,
        "places_found": job.places_found if job is not None else 0,
        "places_saved": job.places_saved if job is not None else 0,
        "total_items": job.total_items if job is not None else 0,
        "processed_items": job.processed_items if job is not None else 0,
        "successful_items": job.successful_items if job is not None else 0,
        "failed_items": job.failed_items if job is not None else 0,
        "retry_count": job.retry_count if job is not None else 0,
        "step_details": details,
        "is_stalled": False if city_published else (is_stalled(job) if job is not None else False),
        "started_at": job.started_at if job is not None else None,
        "finished_at": job.finished_at if job is not None else None,
        "created_at": job.created_at if job is not None else None,
        "updated_at": job.updated_at if job is not None else None,
        "last_error": None if city_published else (job.last_error if job is not None else None),
        "can_run": False if city_published else _can_run(job, city),
        "can_retry": False if city_published else _can_retry(job, raw_status),
        "can_cancel": False if city_published else _can_cancel(job, raw_status),
        "can_publish": False if city_published else _can_publish(city, places_total),
        "can_unpublish": _can_unpublish(city),
        "report_url": f"/admin/routes/data-quality/{city.slug}",
        "logs_url": f"/admin/system-logs?city_slug={city.slug}&module=import",
    }


def _admin_step_details(db: Session, *, city: City, job: CityAdminImportJob | None, places_total: int, places_published: int, pending_photos: int) -> dict[str, object]:
    details = dict(job.step_details or {}) if job is not None else {}
    coverage = _data_coverage(db, city_id=int(city.id), total=places_total, published=places_published, pending_photos=pending_photos)
    changes = import_job_changes_summary(db, city_id=int(city.id)) or {"job_id": job.id if job else None, "city_id": city.id, "city_slug": city.slug, **{key: 0 for key in CHANGE_TYPES}}
    changes = {**changes, "total_changes": sum(int(changes.get(key) or 0) for key in CHANGE_TYPES)}
    details.update({
        "admin_pipeline_contract": {"mode": PIPELINE_MODE, "label": PIPELINE_MODE_LABEL, "collection": "legacy_osm_import", "quality_layer": "foundation_pipeline", "publication_mode": "manual_review_required_for_changed_places"},
        "admin_status_group": _status_group(job.status if job is not None else city.launch_status, job.current_step if job is not None else STEP_QUEUED, city.launch_status, bool(city.is_active)),
        "admin_action_hint": _action_hint(job, city, places_total),
        "admin_auto_refresh_seconds": 7 if job is not None and not _is_published(city) and (job.status in {"queued", "running"} or job.current_step in {STEP_QUEUED, "running"}) else None,
        "data_coverage": coverage,
        "change_summary": changes,
    })
    return details


def _data_coverage(db: Session, *, city_id: int, total: int, published: int, pending_photos: int) -> dict[str, int | float]:
    without_address = db.query(Place).filter(Place.city_id == city_id, Place.address.is_(None)).count()
    without_photo = db.query(Place).filter(Place.city_id == city_id, Place.image_url.is_(None)).count()
    without_description = db.query(Place).filter(Place.city_id == city_id, Place.short_description.is_(None)).count()
    def pct(value: int) -> float:
        return round(((total - value) / total) * 100, 1) if total else 0.0
    return {"places_total": int(total), "places_published": int(published), "places_unpublished": max(int(total) - int(published), 0), "without_address": int(without_address), "without_photo": int(without_photo), "without_description": int(without_description), "address_coverage_pct": pct(int(without_address)), "photo_coverage_pct": pct(int(without_photo)), "description_coverage_pct": pct(int(without_description)), "pending_photos": int(pending_photos)}


def _status_group(status: str, current_step: str, launch_status: str, is_active: bool = False) -> str:
    if launch_status == "published" and is_active:
        return "published"
    if status in {"queued"} or current_step in {STEP_QUEUED, "queued"}:
        return "queued"
    if status == "running":
        return "running"
    if status in {"failed", "stalled", "import_failed"} or launch_status == "import_failed":
        return "failed"
    if current_step == STEP_READY_FOR_REVIEW or status in REVIEWABLE_IMPORT_STATUSES or launch_status == "review_required":
        return "review"
    if launch_status == "published":
        return "published"
    return "idle"


def _action_hint(job: CityAdminImportJob | None, city: City, places_total: int) -> str:
    if _is_published(city):
        return "Город опубликован"
    status = job.status if job is not None else city.launch_status
    if _can_run(job, city):
        return "Запустить сбор"
    if _can_retry(job, status):
        return "Повторить сбор"
    if _can_publish(city, places_total):
        return "Проверить изменения и опубликовать"
    if job is not None and job.status in {"queued", "running"}:
        return "Дождаться завершения import-worker"
    return "Открыть детали"


def _can_run(job: CityAdminImportJob | None, city: City) -> bool:
    if _is_published(city):
        return False
    if job is None:
        return city.launch_status == "importing"
    return job.status in {"queued"} or job.current_step == STEP_QUEUED


def _can_retry(job: CityAdminImportJob | None, status: str) -> bool:
    if job is None:
        return False
    return status in {"failed", "stalled", "import_failed", "success", "success_with_warnings", "partial_success", "cancelled"}


def _can_cancel(job: CityAdminImportJob | None, status: str) -> bool:
    if job is None:
        return False
    if job.current_step in TERMINAL_STEPS:
        return False
    return status in {"running", "queued"} or job.current_step not in TERMINAL_STEPS


def _can_publish(city: City, places_total: int) -> bool:
    return places_total > 0 and city.launch_status in PUBLISHABLE_CITY_STATUSES and not bool(city.is_active)


def _can_unpublish(city: City) -> bool:
    return city.launch_status == "published" and bool(city.is_active)


def _import_next_step(current_step: str, status: str, launch_status: str) -> str:
    if launch_status == "published":
        return "Город опубликован и доступен на сайте."
    if current_step == STEP_READY_FOR_REVIEW or status in {"success", "success_with_warnings", "partial_success", "imported"} or launch_status == "review_required":
        return "Проверьте изменения, качество данных и нажмите «Опубликовать город»."
    if launch_status == "import_failed" and status in {"failed", "stalled", "import_failed"}:
        return "Проверьте качество данных: можно повторить импорт или опубликовать уже собранные места."
    if status in {"failed", "stalled", "import_failed"}:
        return "Проверьте ошибку и нажмите «Повторить сбор»."
    if current_step in {STEP_QUEUED, "queued"}:
        return "Задача стоит в очереди. Import-worker заберёт её автоматически."
    return f"Текущий шаг: {step_label(current_step)}. Экран обновится автоматически."
