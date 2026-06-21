"""Payload import jobs для admin API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.import_pipeline.progress import is_stalled, step_label
from services.import_pipeline.steps import STEP_QUEUED, STEP_READY_FOR_REVIEW, TERMINAL_STEPS

PUBLISHABLE_CITY_STATUSES = {"review_required", "imported", "success", "unpublished"}


def _latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id)
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )


def build_import_job_payload(db: Session, city: City) -> dict[str, object]:
    job = _latest_job(db, city.id)
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
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
    return status in {"failed", "import_failed", "success", "cancelled"}


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
    if current_step == STEP_READY_FOR_REVIEW or status in {"success", "imported"} or launch_status == "review_required":
        return "Проверьте качество данных и нажмите «Опубликовать город»."
    if status in {"failed", "import_failed"}:
        return "Проверьте ошибку и нажмите «Повторить»."
    if current_step in {STEP_QUEUED, "queued"}:
        return "Нажмите «Запустить сейчас», чтобы начать pipeline."
    return f"Текущий шаг: {step_label(current_step)}. Обновите страницу для прогресса."