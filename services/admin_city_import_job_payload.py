"""Payload import jobs для admin API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.import_pipeline.progress import is_stalled, step_label
from services.import_pipeline.steps import STEP_QUEUED, STEP_READY_FOR_REVIEW, TERMINAL_STEPS

PUBLISHABLE_CITY_STATUSES = {
    "review_required",
    "imported",
    "success",
    "success_with_warnings",
    "partial_success",
    "import_failed",
    "unpublished",
}

FAILED_IMPORT_STATUSES = {"failed", "stalled", "import_failed"}
REVIEWABLE_IMPORT_STATUSES = {"success", "success_with_warnings", "partial_success", "imported"}
REVIEWABLE_CITY_STATUSES = {"review_required", "imported"}


def _latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id)
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )


def recover_failed_import_with_places(
    db: Session,
    city: City,
    *,
    places_total: int | None = None,
    job: CityAdminImportJob | None = None,
    actor_id: str = "admin-panel-read",
) -> bool:
    """Move failed imports with saved places into manual review instead of dead error state."""
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
    recovery_details = dict(details.get("failed_import_recovery") or {})
    recovery_details.update({
        "actor_id": actor_id,
        "reason": "failed_import_has_saved_places",
        "places_total": int(total),
        "previous_status": job.status,
        "previous_launch_status": city.launch_status,
        "last_error": job.last_error,
    })
    details["failed_import_recovery"] = recovery_details
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


def normalize_reviewable_import_state(
    db: Session,
    city: City,
    job: CityAdminImportJob | None,
    places_total: int,
    *,
    actor_id: str = "admin-panel-read",
) -> bool:
    """Keep reviewable import payloads consistent with the actual saved places count."""
    if job is None:
        return False
    status = str(job.status or "")
    is_reviewable = (
        city.launch_status in REVIEWABLE_CITY_STATUSES
        or job.current_step == STEP_READY_FOR_REVIEW
        or (status in REVIEWABLE_IMPORT_STATUSES and city.launch_status not in {"draft", "importing", "import_failed"})
    )
    if not is_reviewable:
        return False

    if places_total > 0:
        before = (job.total_items, job.processed_items, job.successful_items, job.places_found, job.places_saved)
        _sync_reviewable_job_counts(job, int(places_total))
        after = (job.total_items, job.processed_items, job.successful_items, job.places_found, job.places_saved)
        if before == after:
            return False
        details = dict(job.step_details or {})
        details["reviewable_count_sync"] = {
            "actor_id": actor_id,
            "reason": "reviewable_import_has_saved_places",
            "places_total": int(places_total),
        }
        job.step_details = details
        db.commit()
        db.refresh(job)
        return True

    reported_places = max(int(job.places_found or 0), int(job.places_saved or 0))
    if reported_places > 0:
        details = dict(job.step_details or {})
        details["place_count_mismatch"] = {
            "actor_id": actor_id,
            "reason": "import_reported_places_missing_from_database",
            "reported_places": reported_places,
            "places_total": 0,
        }
        job.step_details = details
        db.commit()
        db.refresh(job)
        return True

    details = dict(job.step_details or {})
    details["empty_review_recovery"] = {
        "actor_id": actor_id,
        "reason": "reviewable_import_without_saved_places",
        "previous_status": job.status,
        "previous_launch_status": city.launch_status,
        "previous_step": job.current_step,
    }
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
    pending_photos = (
        db.query(PlaceImage)
        .join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
        .count()
    )
    status = job.status if job is not None else city.launch_status
    current_step = job.current_step if job is not None else STEP_QUEUED
    return {
        "id": f"city-import-{city.id}",
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "status": status,
        "launch_status": city.launch_status,
        "is_city_active": bool(city.is_active),
        "current_step": current_step,
        "current_step_label": step_label(current_step),
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
        "step_details": job.step_details if job is not None else None,
        "is_stalled": is_stalled(job) if job is not None else False,
        "started_at": job.started_at if job is not None else None,
        "finished_at": job.finished_at if job is not None else None,
        "created_at": job.created_at if job is not None else None,
        "updated_at": job.updated_at if job is not None else None,
        "last_error": job.last_error if job is not None else None,
        "can_run": _can_run(job, city),
        "can_retry": _can_retry(job, status),
        "can_cancel": _can_cancel(job, status),
        "can_publish": _can_publish(city, places_total),
        "can_unpublish": _can_unpublish(city),
        "report_url": f"/admin/routes/data-quality/{city.slug}",
        "logs_url": f"/admin/system-logs?city_slug={city.slug}&module=import",
    }


def _can_run(job: CityAdminImportJob | None, city: City) -> bool:
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
        return "Проверьте качество данных и нажмите «Опубликовать город»."
    if launch_status == "import_failed" and status in {"failed", "stalled", "import_failed"}:
        return "Проверьте качество данных: можно повторить импорт или опубликовать уже собранные места."
    if status in {"failed", "stalled", "import_failed"}:
        return "Проверьте ошибку и нажмите «Повторить»."
    if current_step in {STEP_QUEUED, "queued"}:
        return "Нажмите «Запустить сейчас», чтобы начать pipeline."
    return f"Текущий шаг: {step_label(current_step)}. Обновите страницу для прогресса."