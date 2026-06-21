"""Оркестратор pipeline: импорт → адреса → фото → качество → readiness."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_log import log_import_event
from services.admin_city_import_runner import run_osm_import_only, summarize_import_results
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.progress import set_step
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

IMAGE_LIMIT = 500
ADDRESS_LIMIT = 500


def run_enrichment_pipeline(
    db: Session,
    *,
    job: CityAdminImportJob,
    city: City,
    actor_id: str,
    force: bool = True,
) -> dict[str, Any]:
    slug = city.slug
    job.status = "running"
    job.started_at = job.started_at or datetime.utcnow()
    city.launch_status = "importing"
    city.is_active = False
    set_step(job, STEP_RUNNING)
    db.commit()
    results: dict[str, Any] = {}

    try:
        set_step(job, STEP_COLLECTING_PLACES)
        log_import_event(db, event="import_step", city_slug=slug, actor_id=actor_id,
                         message="Сбор мест из OSM", details={"step": STEP_COLLECTING_PLACES, "job_id": job.id})
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
        if summary.get("status") != "success":
            raise RuntimeError(str(summary.get("last_error") or "Ошибка импорта OSM"))

        set_step(job, STEP_FINDING_ADDRESSES)
        db.commit()
        addr = run_address_backfill(["--city", slug, "--limit", str(ADDRESS_LIMIT), "--apply"])
        results["addresses"] = addr
        set_step(job, STEP_FINDING_ADDRESSES, processed=int(addr.get("checked") or 0),
                 successful=int(addr.get("updated") or 0), failed=int(addr.get("errors") or 0))
        db.commit()

        set_step(job, STEP_FINDING_IMAGES)
        db.commit()
        images = run_image_enrich(["--city", slug, "--limit", str(IMAGE_LIMIT), "--apply"])
        results["images"] = images
        set_step(job, STEP_FINDING_IMAGES, processed=int(images.get("scanned_places") or 0),
                 successful=int(images.get("created") or 0))
        db.commit()

        set_step(job, STEP_PREPARING_DESCRIPTIONS, detail={"mode": "manual_required",
            "reason": "Автогенерация описаний не подключена. Используйте экспорт enrichment."})
        db.commit()

        set_step(job, STEP_CATEGORIES_TAGS, detail={"mode": "not_implemented",
            "reason": "Теги и нормализация категорий — ручной шаг через админку."})
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
        set_step(job, STEP_READY_FOR_REVIEW, successful=places_total, processed=places_total)
        job.status = "success"
        job.finished_at = datetime.utcnow()
        city.launch_status = "review_required"
        city.is_active = False
        city.last_import_at = job.finished_at
        log_import_event(db, event="import_pipeline_finished", city_slug=slug, actor_id=actor_id,
                         message=f"Pipeline #{job.id} готов к проверке и ручной публикации", details={"job_id": job.id, **results})
        return results
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.last_error = str(exc)[:2000]
        job.finished_at = datetime.utcnow()
        city.launch_status = "import_failed"
        city.is_active = False
        set_step(job, "error", detail={"error": str(exc)})
        log_import_event(db, event="import_pipeline_failed", city_slug=slug, actor_id=actor_id, level="error",
                         message=f"Pipeline #{job.id}: {exc}", details={"job_id": job.id})
        raise