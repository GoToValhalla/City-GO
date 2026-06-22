"""Pipeline обогащения существующего города без повторного OSM-импорта."""

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
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.category_normalize_service import normalize_city_categories
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.progress import set_step
from services.import_pipeline.steps import (
    STEP_CATEGORIES_TAGS,
    STEP_COMPUTING_QUALITY,
    STEP_COMPUTING_READINESS,
    STEP_FINDING_ADDRESSES,
    STEP_FINDING_IMAGES,
    STEP_PREPARING_DESCRIPTIONS,
    STEP_READY_FOR_REVIEW,
    STEP_RUNNING,
)

ADDRESS_LIMIT = 5000
IMAGE_LIMIT = 2000


def run_enrichment_only_pipeline(
    db: Session,
    *,
    job: CityAdminImportJob,
    city: City,
    actor_id: str,
) -> dict[str, Any]:
    slug = city.slug
    job.status = "running"
    job.started_at = job.started_at or datetime.utcnow()
    set_step(job, STEP_RUNNING)
    db.commit()
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    results: dict[str, Any] = {"mode": "enrichment_only", "places_total": places_total}

    try:
        set_step(job, STEP_FINDING_ADDRESSES, total=places_total)
        db.commit()
        addr = run_address_backfill(["--city", slug, "--limit", str(ADDRESS_LIMIT), "--apply"])
        results["addresses"] = addr
        set_step(job, STEP_FINDING_ADDRESSES, processed=int(addr.get("checked") or 0),
                 successful=int(addr.get("updated") or 0), failed=int(addr.get("errors") or 0))
        db.commit()

        set_step(job, STEP_FINDING_IMAGES, total=places_total)
        db.commit()
        images = run_image_enrich(["--city", slug, "--limit", str(IMAGE_LIMIT), "--apply"])
        results["images"] = images
        set_step(job, STEP_FINDING_IMAGES, processed=int(images.get("scanned_places") or 0),
                 successful=int(images.get("created") or 0))
        db.commit()

        set_step(job, STEP_PREPARING_DESCRIPTIONS, detail={"mode": "manual_required",
            "reason": "Автогенерация описаний не подключена"})
        db.commit()

        cats = normalize_city_categories(db, city_slug=slug, apply=True)
        results["categories"] = cats
        set_step(job, STEP_CATEGORIES_TAGS, processed=cats["scanned"], successful=cats["updated"],
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

        set_step(job, STEP_READY_FOR_REVIEW, successful=places_total, processed=places_total)
        job.status = "success"
        job.finished_at = datetime.utcnow()
        city.launch_status = "review_required"
        log_import_event(db, event="enrichment_pipeline_finished", city_slug=slug, actor_id=actor_id,
                         message=f"Обогащение #{job.id} завершено", details={"job_id": job.id, **results})
        return results
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.last_error = str(exc)[:2000]
        job.finished_at = datetime.utcnow()
        set_step(job, "error", detail={"error": str(exc)})
        log_import_event(db, event="enrichment_pipeline_failed", city_slug=slug, actor_id=actor_id,
                         level="error", message=str(exc), details={"job_id": job.id})
        send_admin_alert(
            title="Enrichment pipeline failed",
            message=str(exc)[:1000],
            level="error",
            city_slug=slug,
            job_id=int(job.id),
            details={"status": job.status, "source": job.source, "step_details": job.step_details},
        )
        raise