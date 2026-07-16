"""Pipeline обогащения существующего города без повторного OSM-импорта."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

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

ADDRESS_BATCH_LIMIT = 100
IMAGE_BATCH_LIMIT = 50
ProgressHeartbeat = Callable[[dict[str, Any], int], None]


def run_enrichment_only_pipeline(
    db: Session,
    *,
    job: CityAdminImportJob,
    city: City,
    actor_id: str,
) -> dict[str, Any]:
    slug = city.slug
    # job.status is NOT written here — it stays whatever the caller already
    # set it to ("running", via claim_queued_job) for this entire function's
    # duration. This phase's own outcome is returned in results["status"];
    # the caller applies exactly one final _transition at the very end.
    job.started_at = job.started_at or datetime.utcnow()
    set_step(job, STEP_RUNNING)
    db.commit()
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    results: dict[str, Any] = {"mode": "enrichment_only", "places_total": places_total}

    try:
        set_step(job, STEP_FINDING_ADDRESSES, total=places_total)
        db.commit()
        addr = _run_address_batches(
            slug,
            heartbeat=lambda totals, batches: _heartbeat_enrichment_progress(
                db,
                job,
                STEP_FINDING_ADDRESSES,
                places_total,
                processed=int(totals.get("checked") or 0),
                successful=int(totals.get("updated") or 0),
                failed=int(totals.get("errors") or 0),
                detail={"batches": batches, "last_scanned_place_id": totals.get("last_scanned_place_id")},
            ),
        )
        results["addresses"] = addr
        set_step(
            job,
            STEP_FINDING_ADDRESSES,
            processed=int(addr.get("checked") or 0),
            successful=int(addr.get("updated") or 0),
            failed=int(addr.get("errors") or 0),
            detail={"batches": addr.get("batches"), "last_scanned_place_id": addr.get("last_scanned_place_id")},
        )
        db.commit()

        set_step(job, STEP_FINDING_IMAGES, total=places_total)
        db.commit()
        images = _run_image_batches(
            slug,
            heartbeat=lambda totals, batches: _heartbeat_enrichment_progress(
                db,
                job,
                STEP_FINDING_IMAGES,
                places_total,
                processed=int(totals.get("scanned_places") or 0),
                successful=int(totals.get("created") or 0),
                failed=len(totals.get("errors") or []),
                detail={"batches": batches, "last_scanned_place_id": totals.get("last_scanned_place_id")},
            ),
        )
        results["images"] = images
        set_step(
            job,
            STEP_FINDING_IMAGES,
            processed=int(images.get("scanned_places") or 0),
            successful=int(images.get("created") or 0),
            failed=len(images.get("errors") or []),
            detail={"batches": images.get("batches"), "last_scanned_place_id": images.get("last_scanned_place_id")},
        )
        db.commit()

        set_step(
            job,
            STEP_PREPARING_DESCRIPTIONS,
            detail={"mode": "manual_required", "reason": "Автогенерация описаний не подключена"},
        )
        db.commit()

        cats = normalize_city_categories(db, city_slug=slug, apply=True, job_id=int(job.id))
        results["categories"] = cats
        set_step(
            job,
            STEP_CATEGORIES_TAGS,
            processed=cats["scanned"],
            successful=cats["updated"],
            detail={"mode": "automatic", "category_normalization": cats},
        )
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
        results["status"] = "success"
        job.finished_at = datetime.utcnow()
        city.launch_status = "review_required"
        log_import_event(
            db,
            event="enrichment_pipeline_finished",
            city_slug=slug,
            actor_id=actor_id,
            message=f"Обогащение #{job.id} завершено",
            details={"job_id": job.id, **results},
        )
        db.commit()
        db.refresh(job)
        db.refresh(city)
        send_admin_alert(
            title="Enrichment pipeline finished",
            message=f"{city.name} готов к проверке после обогащения. Мест обработано: {places_total}.",
            level="info",
            city_slug=slug,
            job_id=int(job.id),
            details={"status": "success", "source": job.source, "places_total": places_total, "readiness": readiness},
        )
        return results
    except Exception as exc:  # noqa: BLE001
        results["status"] = "failed"
        job.last_error = str(exc)[:2000]
        job.finished_at = datetime.utcnow()
        set_step(job, "error", detail={"error": str(exc)})
        log_import_event(
            db,
            event="enrichment_pipeline_failed",
            city_slug=slug,
            actor_id=actor_id,
            level="error",
            message=str(exc),
            details={"job_id": job.id},
        )
        send_admin_alert(
            title="Enrichment pipeline failed",
            message=str(exc)[:1000],
            level="error",
            city_slug=slug,
            job_id=int(job.id),
            details={"status": "failed", "source": job.source, "step_details": job.step_details},
        )
        raise


def _heartbeat_enrichment_progress(
    db: Session,
    job: CityAdminImportJob,
    step: str,
    total: int,
    *,
    processed: int,
    successful: int,
    failed: int,
    detail: dict[str, object],
) -> None:
    set_step(job, step, total=total, processed=processed, successful=successful, failed=failed, detail=detail)
    db.commit()


def _run_address_batches(slug: str, heartbeat: ProgressHeartbeat | None = None) -> dict[str, Any]:
    cursor = 0
    batches = 0
    totals: dict[str, Any] = {
        "checked": 0,
        "updated": 0,
        "verified_existing": 0,
        "sent_to_review": 0,
        "skipped_no_coordinates": 0,
        "skipped_generic_result": 0,
        "skipped_existing_address": 0,
        "cleared_placeholders": 0,
        "errors": 0,
        "last_scanned_place_id": 0,
    }

    while True:
        batch = run_address_backfill(
            [
                "--city",
                slug,
                "--limit",
                str(ADDRESS_BATCH_LIMIT),
                "--start-after-id",
                str(cursor),
                "--apply",
            ]
        )
        batches += 1
        _add_int_counts(totals, batch, [
            "checked",
            "updated",
            "verified_existing",
            "sent_to_review",
            "skipped_no_coordinates",
            "skipped_generic_result",
            "skipped_existing_address",
            "cleared_placeholders",
            "errors",
        ])
        last_id = int(batch.get("last_scanned_place_id") or 0)
        totals["last_scanned_place_id"] = max(int(totals["last_scanned_place_id"] or 0), last_id)
        if heartbeat is not None:
            heartbeat(totals, batches)
        if last_id <= cursor:
            break
        cursor = last_id
        if int(batch.get("checked") or 0) < ADDRESS_BATCH_LIMIT:
            break

    totals["batches"] = batches
    return totals


def _run_image_batches(slug: str, heartbeat: ProgressHeartbeat | None = None) -> dict[str, Any]:
    cursor = 0
    batches = 0
    totals: dict[str, Any] = {
        "scanned_places": 0,
        "candidates_found": 0,
        "created": 0,
        "auto_approved": 0,
        "place_image_url_synced": 0,
        "skipped_duplicates": 0,
        "skipped_has_approved": 0,
        "skipped_ineligible": 0,
        "skipped_no_source": 0,
        "errors": [],
        "last_scanned_place_id": 0,
    }

    while True:
        batch = run_image_enrich(
            [
                "--city",
                slug,
                "--limit",
                str(IMAGE_BATCH_LIMIT),
                "--start-after-id",
                str(cursor),
                "--apply",
            ]
        )
        batches += 1
        _add_int_counts(totals, batch, [
            "scanned_places",
            "candidates_found",
            "created",
            "auto_approved",
            "place_image_url_synced",
            "skipped_duplicates",
            "skipped_has_approved",
            "skipped_ineligible",
            "skipped_no_source",
        ])
        errors = batch.get("errors") or []
        if isinstance(errors, list):
            totals["errors"].extend(errors)
        last_id = int(batch.get("last_scanned_place_id") or 0)
        totals["last_scanned_place_id"] = max(int(totals["last_scanned_place_id"] or 0), last_id)
        if heartbeat is not None:
            heartbeat(totals, batches)
        scanned = int(batch.get("scanned_places") or 0)
        if last_id <= cursor or scanned <= 0:
            break
        cursor = last_id
        if scanned < IMAGE_BATCH_LIMIT:
            break

    totals["batches"] = batches
    return totals


def _add_int_counts(target: dict[str, Any], source: dict[str, object], keys: list[str]) -> None:
    for key in keys:
        target[key] = int(target.get(key) or 0) + int(source.get(key) or 0)
