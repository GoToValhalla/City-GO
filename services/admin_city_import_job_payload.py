"""Payload import jobs для admin API."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_import_job_change_service import CHANGE_TYPES
from services.admin_import_display import (
    effective_failed_items,
    import_error_summary,
    import_execution_summary,
    is_active_import_job,
    is_published_city,
    job_execution_failed,
    pipeline_warnings,
    resolve_import_display,
    snapshot_warning,
    stale_import_error,
)
from services.import_pipeline.progress import is_stalled, step_label
from services.photo_enrichment_diagnostics import build_photo_enrichment_diagnostics
from services.import_pipeline.steps import STEP_QUEUED, STEP_READY_FOR_REVIEW, TERMINAL_STEPS

PUBLISHABLE_CITY_STATUSES = {"review_required", "imported", "success", "success_with_warnings", "partial_success", "import_failed", "unpublished"}
FAILED_IMPORT_STATUSES = {"failed", "stalled", "import_failed"}
REVIEWABLE_IMPORT_STATUSES = {"success", "success_with_warnings", "partial_success", "imported"}
REVIEWABLE_CITY_STATUSES = {"review_required", "imported"}
PIPELINE_MODE = "legacy_osm_plus_foundation"
PIPELINE_MODE_LABEL = "OSM сбор + foundation quality layer"
SNAPSHOT_KEY = "admin_import_snapshot"
SOURCE_PHOTO_ENRICHMENT = "admin_photo_enrichment"
SOURCE_ADDRESS_ENRICHMENT = "admin_address_enrichment"


def _latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city_id).order_by(CityAdminImportJob.created_at.desc()).first()


def _latest_job_by_source(db: Session, city_id: int, source: str) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id, CityAdminImportJob.source == source)
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )


def _latest_step_result(db: Session, city_id: int, *, source: str, key: str) -> dict[str, object] | None:
    job = _latest_job_by_source(db, city_id, source)
    if job is None:
        return None
    value = dict(job.step_details or {}).get(key)
    if not isinstance(value, dict):
        return None
    return {**value, "job_id": job.id, "job_status": job.status, "job_source": job.source, "finished_at": job.finished_at.isoformat() if job.finished_at else None}


def _is_published(city: City) -> bool:
    return is_published_city(city)


def _is_active_job(job: CityAdminImportJob | None) -> bool:
    return is_active_import_job(job)


def recover_failed_import_with_places(db: Session, city: City, *, places_total: int | None = None, job: CityAdminImportJob | None = None, actor_id: str = "admin-panel-read") -> bool:
    """Deprecated compatibility shim. Recovery must not run during GET/read flows."""
    return False


def normalize_reviewable_import_state(db: Session, city: City, job: CityAdminImportJob | None, places_total: int, *, actor_id: str = "admin-panel-read") -> bool:
    """Deprecated compatibility shim. GET/read flows are read-only."""
    return False


def _sync_reviewable_job_counts(job: CityAdminImportJob, places_total: int) -> None:
    job.total_items = max(int(job.total_items or 0), places_total)
    job.processed_items = max(int(job.processed_items or 0), places_total)
    job.successful_items = max(int(job.successful_items or 0), places_total)
    job.places_found = max(int(job.places_found or 0), places_total)
    job.places_saved = max(int(job.places_saved or 0), places_total)


def build_import_job_payload(db: Session, city: City) -> dict[str, object]:
    job = _latest_job(db, city.id)
    snapshot = _snapshot(job)
    coverage = _snapshot_coverage(snapshot)
    changes = _snapshot_changes(snapshot)
    places_total = int(coverage.get("places_total") or 0)
    places_published = int(coverage.get("places_published") or 0)
    pending_photos = int(coverage.get("pending_photos") or 0)
    if not snapshot:
        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        places_published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
        pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    city_published = _is_published(city)
    active_job = _is_active_job(job)
    display = resolve_import_display(city, job)
    status = display["display_status"]
    current_step = display["display_step"]
    details = _admin_step_details(
        db=db,
        city=city,
        job=job,
        places_total=int(places_total),
        places_published=int(places_published),
        pending_photos=int(pending_photos),
        snapshot=snapshot,
        status_group=str(display["status_group"]),
    )
    failed_items = effective_failed_items(job)
    execution_summary = import_execution_summary(job, places_published=int(places_published))
    error_summary = import_error_summary(job)
    current_warnings = pipeline_warnings(job)
    stale_error = stale_import_error(job)
    snap_warn = snapshot_warning(snapshot)
    photo_diagnostics = _photo_diagnostics_for_city(db, city, job=job, details=details)
    details["photo_diagnostics"] = photo_diagnostics
    return {
        "id": f"city-import-{city.id}",
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "status": status,
        "job_execution_status": display["job_execution_status"],
        "destination_publication_status": display["destination_publication_status"],
        "launch_status": city.launch_status,
        "is_city_active": bool(city.is_active),
        "current_step": current_step,
        "current_step_label": display["display_step_label"],
        "source": job.source if job is not None else "admin_city_import",
        "pipeline_mode": PIPELINE_MODE,
        "pipeline_mode_label": PIPELINE_MODE_LABEL,
        "status_group": display["status_group"],
        "action_hint": _action_hint(job, city, places_total),
        "auto_refresh_seconds": 7 if active_job else None,
        "data_coverage": coverage,
        "change_summary": changes,
        "places_total": places_total,
        "places_published": places_published,
        "places_unpublished": max(places_total - places_published, 0),
        "pending_photos": pending_photos,
        "photo_diagnostics": photo_diagnostics,
        "next_step": _import_next_step(current_step, status, city.launch_status) if snapshot else "Snapshot ещё не создан. Нажмите «Обновить snapshot», чтобы увидеть coverage и отчёт изменений без тяжёлого GET.",
        "job_id": job.id if job is not None else None,
        "scopes_total": job.scopes_total if job is not None else 0,
        "scopes_succeeded": job.scopes_succeeded if job is not None else 0,
        "places_found": job.places_found if job is not None else 0,
        "places_saved": job.places_saved if job is not None else 0,
        "total_items": job.total_items if job is not None else 0,
        "processed_items": job.processed_items if job is not None else 0,
        "successful_items": job.successful_items if job is not None else 0,
        "failed_items": failed_items,
        "retry_count": job.retry_count if job is not None else 0,
        "step_details": details,
        "import_execution_summary": execution_summary,
        "import_error_summary": error_summary,
        "current_warnings": current_warnings,
        "stale_error": None if display["suppress_job_errors"] else stale_error,
        "snapshot_warning": snap_warn,
        "is_stalled": is_stalled(job) if job is not None else False,
        "job_execution_failed": job_execution_failed(job),
        "started_at": job.started_at if job is not None else None,
        "finished_at": job.finished_at if job is not None else None,
        "created_at": job.created_at if job is not None else None,
        "updated_at": job.updated_at if job is not None else None,
        "last_error": None if display["suppress_job_errors"] else (job.last_error if job is not None else None),
        "can_run": False if city_published else _can_run(job, city),
        "can_retry": False if active_job else _can_retry(job, str(display["job_execution_status"])),
        "can_cancel": active_job and _can_cancel(job, str(display["job_execution_status"])),
        "can_publish": False if active_job or (city_published and not job_execution_failed(job)) else _can_publish(city, places_total),
        "can_unpublish": _can_unpublish(city),
        "report_url": f"/admin/routes/data-quality/{city.slug}",
        "logs_url": f"/admin/system-logs?city_slug={city.slug}&module=import",
    }


def refresh_import_job_snapshot(db: Session, *, city_id: int, source: str = "explicit_refresh") -> dict[str, object]:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _latest_job(db, city.id)
    if job is None:
        job = CityAdminImportJob(city_id=city.id, status="success", source="admin_snapshot_refresh", current_step="snapshot_refresh")
        db.add(job)
        db.flush()
    total = db.query(Place).filter(Place.city_id == city.id).count()
    published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
    pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    coverage = _data_coverage(db, city_id=int(city.id), total=int(total), published=int(published), pending_photos=int(pending_photos))
    changes = _cached_change_summary(job, city)
    changes = {**changes, "total_changes": sum(int(changes.get(key) or 0) for key in CHANGE_TYPES)}
    snapshot = {"version": 1, "source": source, "taken_at": datetime.utcnow().isoformat(), "city_id": city.id, "city_slug": city.slug, "job_id": job.id, "data_coverage": coverage, "change_summary": changes}
    details = dict(job.step_details or {})
    details[SNAPSHOT_KEY] = snapshot
    details["data_coverage"] = coverage
    details["change_summary"] = changes
    latest_photo = _latest_step_result(db, int(city.id), source=SOURCE_PHOTO_ENRICHMENT, key="photo_enrichment")
    if latest_photo:
        details["latest_photo_enrichment"] = latest_photo
    job.step_details = details
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return snapshot


def _admin_step_details(*, db: Session, city: City, job: CityAdminImportJob | None, places_total: int, places_published: int, pending_photos: int, snapshot: dict[str, object] | None, status_group: str) -> dict[str, object]:
    details = dict(job.step_details or {}) if job is not None else {}
    coverage = _snapshot_coverage(snapshot)
    changes = _snapshot_changes(snapshot)
    latest_photo = _latest_step_result(db, int(city.id), source=SOURCE_PHOTO_ENRICHMENT, key="photo_enrichment")
    latest_address = _latest_step_result(db, int(city.id), source=SOURCE_ADDRESS_ENRICHMENT, key="address_enrichment")
    if latest_photo:
        details["latest_photo_enrichment"] = latest_photo
        details.setdefault("photo_enrichment", latest_photo)
    if latest_address:
        details["latest_address_enrichment"] = latest_address
    details["photo_diagnostics"] = _photo_diagnostics_for_city(db, city, job=job, details=details)
    details.update({
        "admin_pipeline_contract": {"mode": PIPELINE_MODE, "label": PIPELINE_MODE_LABEL, "collection": "legacy_osm_import", "quality_layer": "foundation_pipeline", "publication_mode": "manual_review_required_for_changed_places"},
        "admin_status_group": status_group,
        "admin_action_hint": _action_hint(job, city, places_total),
        "admin_auto_refresh_seconds": 7 if _is_active_job(job) else None,
        "snapshot_at": snapshot.get("taken_at") if snapshot else None,
        "snapshot_source": snapshot.get("source") if snapshot else "missing",
        "snapshot_stale": not bool(snapshot),
        "data_coverage": coverage,
        "change_summary": changes,
    })
    return details


def _photo_diagnostics_for_city(
    db: Session,
    city: City,
    *,
    job: CityAdminImportJob | None,
    details: dict[str, object],
) -> dict[str, object]:
    enrichment = details.get("photo_enrichment") or details.get("latest_photo_enrichment")
    enrichment_dict = enrichment if isinstance(enrichment, dict) else None
    step_status = None
    dependency_step = None
    warnings = details.get("warnings")
    if isinstance(warnings, list):
        for row in warnings:
            if isinstance(row, dict) and row.get("reason") == "dependency_failed" and row.get("step") == "finding_images":
                step_status = "skipped"
                dependency_step = str(row.get("dependency") or "collecting_places")
    return build_photo_enrichment_diagnostics(
        db,
        city,
        enrichment_result=enrichment_dict,
        step_status=step_status,
        dependency_step=dependency_step,
        scan_limit=2000,
    )


def _snapshot(job: CityAdminImportJob | None) -> dict[str, object] | None:
    if job is None:
        return None
    value = (job.step_details or {}).get(SNAPSHOT_KEY)
    return value if isinstance(value, dict) else None


def _snapshot_coverage(snapshot: dict[str, object] | None) -> dict[str, object]:
    value = (snapshot or {}).get("data_coverage")
    return value if isinstance(value, dict) else {}


def _snapshot_changes(snapshot: dict[str, object] | None) -> dict[str, object]:
    value = (snapshot or {}).get("change_summary")
    return value if isinstance(value, dict) else {}


def _cached_change_summary(job: CityAdminImportJob, city: City) -> dict[str, object]:
    value = dict(job.step_details or {}).get("change_summary")
    if isinstance(value, dict):
        return dict(value)
    return {"job_id": job.id, "city_id": city.id, "city_slug": city.slug, **{key: 0 for key in CHANGE_TYPES}}


def _data_coverage(db: Session, *, city_id: int, total: int, published: int, pending_photos: int) -> dict[str, int | float]:
    without_address = db.query(Place).filter(Place.city_id == city_id, Place.address.is_(None)).count()
    without_photo = db.query(Place).filter(Place.city_id == city_id, Place.image_url.is_(None)).count()
    without_description = db.query(Place).filter(Place.city_id == city_id, Place.short_description.is_(None)).count()
    def pct(value: int) -> float:
        return round(((total - value) / total) * 100, 1) if total else 0.0
    return {"places_total": int(total), "places_published": int(published), "places_unpublished": max(int(total) - int(published), 0), "without_address": int(without_address), "without_photo": int(without_photo), "without_description": int(without_description), "address_coverage_pct": pct(int(without_address)), "photo_coverage_pct": pct(int(without_photo)), "description_coverage_pct": pct(int(without_description)), "pending_photos": int(pending_photos)}


def _status_group(status: str, current_step: str, launch_status: str, is_active: bool = False) -> str:
    if status in FAILED_IMPORT_STATUSES:
        return "failed"
    if status == "queued":
        return "queued"
    if status == "running":
        return "running"
    if launch_status == "published" and is_active:
        return "published"
    if status in {"failed", "stalled", "import_failed"} or launch_status == "import_failed":
        return "failed"
    if current_step == STEP_READY_FOR_REVIEW or status in REVIEWABLE_IMPORT_STATUSES or launch_status == "review_required":
        return "review"
    if launch_status == "published":
        return "published"
    return "idle"


def _action_hint(job: CityAdminImportJob | None, city: City, places_total: int) -> str:
    if job is not None and job.status in {"queued", "running"}:
        return "Дождаться завершения import-worker"
    if _is_published(city):
        return "Город опубликован"
    status = job.status if job is not None else city.launch_status
    if _can_run(job, city):
        return "Запустить сбор"
    if _can_retry(job, status):
        return "Повторить сбор"
    if _can_publish(city, places_total):
        return "Проверить изменения и опубликовать"
    return "Открыть детали"


def _can_run(job: CityAdminImportJob | None, city: City) -> bool:
    if _is_published(city):
        return False
    if job is None:
        return city.launch_status == "importing"
    return False


def _can_retry(job: CityAdminImportJob | None, status: str) -> bool:
    if job is None:
        return status in {"import_failed", "failed", "stalled"}
    return status in {"failed", "stalled", "import_failed", "success", "success_with_warnings", "partial_success", "cancelled"}


def _can_cancel(job: CityAdminImportJob | None, status: str) -> bool:
    if job is None:
        return False
    return status in {"running", "queued"} and job.current_step not in TERMINAL_STEPS


def _can_publish(city: City, places_total: int) -> bool:
    return places_total > 0 and city.launch_status in PUBLISHABLE_CITY_STATUSES and not bool(city.is_active)


def _can_unpublish(city: City) -> bool:
    return city.launch_status == "published" and bool(city.is_active)


def _import_next_step(current_step: str, status: str, launch_status: str) -> str:
    if status in {"running", "queued"} or current_step == "snapshot_refresh":
        return "Фоновая задача выполняется. Дождитесь завершения import-worker."
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
