"""Оркестратор pipeline: импорт → адреса → фото → качество → readiness."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.admin_city_import_runner import run_osm_import_only, summarize_import_results
from services.category_normalize_service import normalize_city_categories
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.progress import append_step_warning, set_step
from services.import_pipeline.steps import (
    STEP_CATEGORIES_TAGS,
    STEP_COLLECTING_PLACES,
    STEP_COMPUTING_QUALITY,
    STEP_COMPUTING_READINESS,
    STEP_FINDING_ADDRESSES,
    STEP_FINDING_IMAGES,
    STEP_PREPARING_DESCRIPTIONS,
    STEP_READY_FOR_REVIEW,
    STEP_RUNNING,
)

IMAGE_LIMIT = 2000
ADDRESS_LIMIT = 5000


def run_enrichment_pipeline(
    db: Session,
    *,
    job: CityAdminImportJob,
    city: City,
    actor_id: str,
    force: bool = True,
    notify_completion: bool = True,
) -> dict[str, Any]:
    slug = city.slug
    job.status = "running"
    job.started_at = job.started_at or datetime.utcnow()
    city.launch_status = "importing"
    city.is_active = False
    set_step(job, STEP_RUNNING)
    db.commit()
    results: dict[str, Any] = {}
    warnings: list[dict[str, object]] = []

    try:
        set_step(job, STEP_COLLECTING_PLACES)
        _log_worker_step(db, job=job, city_slug=slug, actor_id=actor_id, step=STEP_COLLECTING_PLACES, status="started")
        db.commit()
        payload = run_osm_import_only(slug, force=force)
        summary = summarize_import_results(payload)
        results["import"] = summary
        job.scopes_succeeded = int(summary.get("scopes_succeeded") or 0)
        job.places_found = int(summary.get("places_found") or 0)
        job.places_saved = int(summary.get("places_saved") or 0)
        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        set_step(job, STEP_COLLECTING_PLACES, total=places_total, processed=places_total,
                 successful=int(summary.get("places_saved") or 0))
        db.commit()
        if summary.get("status") != "success" and places_total <= 0:
            raise RuntimeError(str(summary.get("last_error") or "Ошибка импорта OSM"))
        if summary.get("status") != "success":
            warnings.append({"step": STEP_COLLECTING_PLACES, "error": str(summary.get("last_error") or "partial import")})
            append_step_warning(job, STEP_COLLECTING_PLACES, summary.get("last_error") or "partial import")
        _log_worker_step(db, job=job, city_slug=slug, actor_id=actor_id, step=STEP_COLLECTING_PLACES,
                         status=str(summary.get("status") or "unknown"), raw_count=job.places_found,
                         created=job.places_saved, accepted_count=places_total)

        addr = _optional_pipeline_step(
            db,
            job=job,
            city_slug=slug,
            actor_id=actor_id,
            step=STEP_FINDING_ADDRESSES,
            warnings=warnings,
            action=lambda: run_address_backfill(["--city", slug, "--limit", str(ADDRESS_LIMIT), "--apply"]),
        )
        results["addresses"] = addr
        if isinstance(addr, dict):
            set_step(job, STEP_FINDING_ADDRESSES, processed=int(addr.get("checked") or 0),
                     successful=int(addr.get("updated") or 0), failed=int(addr.get("errors") or 0))
            db.commit()

        images = _optional_pipeline_step(
            db,
            job=job,
            city_slug=slug,
            actor_id=actor_id,
            step=STEP_FINDING_IMAGES,
            warnings=warnings,
            action=lambda: run_image_enrich(["--city", slug, "--limit", str(IMAGE_LIMIT), "--apply"]),
        )
        results["images"] = images
        if isinstance(images, dict):
            set_step(job, STEP_FINDING_IMAGES, processed=int(images.get("scanned_places") or 0),
                     successful=int(images.get("created") or 0),
                     failed=int(images.get("failed_image_lookup") or images.get("failed") or 0),
                     detail={"image_enrichment": {
                         "scanned_places": int(images.get("scanned_places") or 0),
                         "created_images": int(images.get("created_images") or images.get("created") or 0),
                         "failed_image_lookup": int(images.get("failed_image_lookup") or images.get("failed") or 0),
                     }})
            db.commit()

        set_step(job, STEP_PREPARING_DESCRIPTIONS, detail={"mode": "manual_required",
            "reason": "Автогенерация описаний не подключена. Используйте экспорт enrichment."})
        db.commit()

        cats = normalize_city_categories(db, city_slug=slug, apply=True)
        results["categories"] = cats
        set_step(job, STEP_CATEGORIES_TAGS, processed=int(cats.get("scanned") or 0),
                 successful=int(cats.get("updated") or 0), failed=int(cats.get("skipped") or 0),
                 detail={"mode": "automatic", "category_normalization": cats})
        db.commit()

        set_step(job, STEP_COMPUTING_QUALITY)
        db.commit()
        quality = run_quality_cleanup(["--city", slug, "--apply"])
        results["quality"] = quality
        db.commit()

        set_step(job, STEP_COMPUTING_READINESS)
        db.commit()
        readiness = compute_city_readiness(db, city_slug=slug) or {}
        results["readiness"] = readiness
        set_step(job, STEP_COMPUTING_READINESS, detail={"readiness_score": readiness.get("readiness_score")})
        db.commit()

        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        if places_total <= 0:
            raise RuntimeError("OSM import finished without places")
        set_step(job, STEP_READY_FOR_REVIEW, successful=places_total, processed=places_total)
        job.status = "success_with_warnings" if warnings else "success"
        job.finished_at = datetime.utcnow()
        city.launch_status = "review_required"
        city.is_active = False
        city.last_import_at = job.finished_at
        if warnings:
            job.step_details = {**dict(job.step_details or {}), "warnings": warnings}
        log_import_event(db, event="import_pipeline_finished", city_slug=slug, actor_id=actor_id,
                         message=f"Pipeline #{job.id} готов к проверке и ручной публикации", details={"job_id": job.id, **results})
        db.commit()
        db.refresh(job)
        db.refresh(city)
        alert_details = {
            "places_total": places_total,
            "readiness": results.get("readiness"),
            "warnings": warnings,
            "status": job.status,
            "source": job.source,
        }
        if notify_completion:
            if warnings:
                send_admin_alert(
                    title="Import completed with warnings",
                    message="Импорт завершён, но некоторые необязательные шаги требуют внимания.",
                    level="warning",
                    city_slug=slug,
                    job_id=int(job.id),
                    details=alert_details,
                )
            else:
                send_admin_alert(
                    title="Import pipeline finished",
                    message=f"{city.name} готов к проверке. Мест собрано: {places_total}.",
                    level="info",
                    city_slug=slug,
                    job_id=int(job.id),
                    details=alert_details,
                )
        return results
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        failed_step = job.current_step or "unknown"
        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        job.last_error = error_text[:2000]
        job.finished_at = datetime.utcnow()
        city.is_active = False

        if places_total > 0:
            append_step_warning(job, failed_step, exc, extra={"recovered_as": "partial_success"})
            recovery_detail = {
                "step": failed_step,
                "error": error_text[:1000],
                "places_total": places_total,
            }
            set_step(
                job,
                STEP_READY_FOR_REVIEW,
                total=places_total,
                processed=places_total,
                successful=places_total,
                detail={"partial_success_after_error": recovery_detail},
            )
            job.status = "partial_success"
            city.launch_status = "review_required"
            city.last_import_at = job.finished_at
            results["partial_success_after_error"] = recovery_detail
            log_import_event(
                db,
                event="import_pipeline_partial_success",
                city_slug=slug,
                actor_id=actor_id,
                level="warning",
                message=f"Pipeline #{job.id}: места сохранены, требуется ручная проверка после ошибки: {error_text}",
                details={"job_id": job.id, **recovery_detail},
            )
            db.commit()
            db.refresh(job)
            db.refresh(city)
            if notify_completion:
                send_admin_alert(
                    title="Import completed with warnings",
                    message=f"{city.name} переведён на ручную проверку после ошибки.",
                    level="warning",
                    city_slug=slug,
                    job_id=int(job.id),
                    details={
                        "status": job.status,
                        "source": job.source,
                        "places_total": places_total,
                        "warnings": [recovery_detail],
                    },
                )
            return results

        job.status = "failed"
        city.launch_status = "import_failed"
        set_step(job, "error", detail={"error": error_text})
        log_import_event(db, event="import_pipeline_failed", city_slug=slug, actor_id=actor_id, level="error",
                         message=f"Pipeline #{job.id}: {exc}", details={"job_id": job.id})
        db.commit()
        send_admin_alert(
            title="Import pipeline failed",
            message=error_text[:1000],
            level="error",
            city_slug=slug,
            job_id=int(job.id),
            details={"status": job.status, "source": job.source, "step_details": job.step_details},
        )
        raise


def _optional_pipeline_step(
    db: Session,
    *,
    job: CityAdminImportJob,
    city_slug: str,
    actor_id: str,
    step: str,
    warnings: list[dict[str, object]],
    action,
) -> dict[str, Any]:
    set_step(job, step)
    _log_worker_step(db, job=job, city_slug=city_slug, actor_id=actor_id, step=step, status="started")
    db.commit()
    try:
        result = action()
        _log_worker_step(db, job=job, city_slug=city_slug, actor_id=actor_id, step=step, status="success", **_step_counts(result))
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:  # noqa: BLE001
        warning = {"step": step, "error": str(exc)[:1000]}
        warnings.append(warning)
        append_step_warning(job, step, exc)
        _log_worker_step(db, job=job, city_slug=city_slug, actor_id=actor_id, step=step, status="warning", error=str(exc))
        db.commit()
        return {"status": "warning", "error": str(exc)[:1000]}


def _step_counts(result: object) -> dict[str, object]:
    if not isinstance(result, dict):
        return {}
    return {
        "raw_count": result.get("raw_count"),
        "accepted_count": result.get("normalized_count") or result.get("accepted_count"),
        "created": result.get("created") or result.get("created_images"),
        "updated": result.get("updated"),
        "rejected": result.get("rejected") or result.get("failed_image_lookup"),
    }


def _log_worker_step(
    db: Session,
    *,
    job: CityAdminImportJob,
    city_slug: str,
    actor_id: str,
    step: str,
    status: str,
    **details: object,
) -> None:
    payload = {"city_slug": city_slug, "job_id": job.id, "step": step, "status": status, **details}
    print(json.dumps(payload, ensure_ascii=False, default=str))
    log_import_event(db, event="import_step", city_slug=city_slug, actor_id=actor_id,
                     message=f"{step}: {status}", details=payload)
