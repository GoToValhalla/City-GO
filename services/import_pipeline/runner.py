"""Оркестратор pipeline: импорт → адреса → фото → качество → readiness."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.admin_city_import_runner import run_osm_import_only, summarize_import_results
from services.category_normalize_service import normalize_places_categories
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
from services.place_import_lifecycle_service import mark_place_for_review

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
    original_city_state = (city.launch_status, bool(city.is_active))
    pipeline_started_at = datetime.utcnow()
    job.status = "running"
    job.started_at = job.started_at or pipeline_started_at
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
        set_step(
            job,
            STEP_COLLECTING_PLACES,
            total=places_total,
            processed=places_total,
            successful=int(summary.get("places_saved") or 0),
            detail={"import_diff": summary},
        )
        db.commit()
        if summary.get("status") != "success" and places_total <= 0:
            raise RuntimeError(str(summary.get("last_error") or "Ошибка импорта OSM"))
        if summary.get("status") != "success":
            warning = {"step": STEP_COLLECTING_PLACES, "error": str(summary.get("last_error") or "partial import")}
            warnings.append(warning)
            append_step_warning(job, STEP_COLLECTING_PLACES, warning["error"])
        _log_worker_step(
            db,
            job=job,
            city_slug=slug,
            actor_id=actor_id,
            step=STEP_COLLECTING_PLACES,
            status=str(summary.get("status") or "unknown"),
            raw_count=job.places_found,
            created=int(summary.get("created") or 0),
            updated=int(summary.get("updated") or 0),
            accepted_count=places_total,
        )

        addresses = _optional_pipeline_step(
            db,
            job=job,
            city_slug=slug,
            actor_id=actor_id,
            step=STEP_FINDING_ADDRESSES,
            warnings=warnings,
            action=lambda: run_address_backfill(["--city", slug, "--limit", str(ADDRESS_LIMIT), "--apply"]),
        )
        results["addresses"] = addresses
        if isinstance(addresses, dict):
            set_step(
                job,
                STEP_FINDING_ADDRESSES,
                processed=int(addresses.get("checked") or 0),
                successful=int(addresses.get("updated") or 0),
                failed=int(addresses.get("errors") or 0),
            )
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
            set_step(
                job,
                STEP_FINDING_IMAGES,
                processed=int(images.get("scanned_places") or 0),
                successful=int(images.get("created") or 0),
                failed=int(images.get("failed_image_lookup") or images.get("failed") or 0),
                detail={"image_enrichment": images},
            )
            db.commit()

        db.expire_all()
        changed_places = _changed_places(db, city_id=city.id, since=pipeline_started_at)
        for place in changed_places:
            mark_place_for_review(place, reason="import_or_enrichment_changed")
        db.commit()

        set_step(
            job,
            STEP_PREPARING_DESCRIPTIONS,
            detail={"mode": "manual_required", "reason": "Автогенерация описаний не подключена."},
        )
        categories = normalize_places_categories(db, places=changed_places, apply=True)
        results["categories"] = categories
        set_step(
            job,
            STEP_CATEGORIES_TAGS,
            processed=int(categories.get("scanned") or 0),
            successful=int(categories.get("updated") or 0),
            failed=int(categories.get("skipped") or 0),
            detail={"mode": "changed_places_only", "category_normalization": categories},
        )
        db.commit()

        # Quality V2 and publication decisions run in the foundation pipeline,
        # which receives exactly these changed place IDs.
        changed_place_ids = sorted({int(place.id) for place in changed_places})
        results["changed_place_ids"] = changed_place_ids
        results["has_changes"] = bool(changed_place_ids)
        results["quality"] = {"mode": "foundation", "changed_places": len(changed_place_ids)}
        set_step(job, STEP_COMPUTING_QUALITY, processed=len(changed_place_ids), detail=results["quality"])

        set_step(job, STEP_COMPUTING_READINESS)
        readiness = compute_city_readiness(db, city_slug=slug) or {}
        results["readiness"] = readiness
        set_step(job, STEP_COMPUTING_READINESS, detail={"readiness_score": readiness.get("readiness_score")})

        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        if places_total <= 0:
            raise RuntimeError("OSM import finished without places")
        set_step(job, STEP_READY_FOR_REVIEW, successful=len(changed_place_ids), processed=len(changed_place_ids))
        job.status = "success_with_warnings" if warnings else "success"
        job.finished_at = datetime.utcnow()
        job.step_details = {
            **dict(job.step_details or {}),
            "warnings": warnings,
            "changed_place_ids": changed_place_ids,
            "has_changes": bool(changed_place_ids),
            "import_summary": summary,
        }
        if changed_place_ids:
            city.launch_status = "review_required"
            city.is_active = False
        else:
            city.launch_status, city.is_active = original_city_state
        city.last_import_at = job.finished_at
        log_import_event(
            db,
            event="import_pipeline_finished",
            city_slug=slug,
            actor_id=actor_id,
            message=(
                f"Pipeline #{job.id}: {len(changed_place_ids)} мест требуют проверки"
                if changed_place_ids
                else f"Pipeline #{job.id}: изменений нет, публикация сохранена"
            ),
            details={"job_id": job.id, **results},
        )
        db.commit()
        db.refresh(job)
        db.refresh(city)

        if notify_completion:
            _notify_completion(
                city=city,
                job=job,
                places_total=places_total,
                changed_count=len(changed_place_ids),
                readiness=readiness,
                warnings=warnings,
            )
        return results
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        db.expire_all()
        changed_places = _changed_places(db, city_id=city.id, since=pipeline_started_at)
        changed_place_ids = sorted({int(place.id) for place in changed_places})
        for place in changed_places:
            mark_place_for_review(place, reason="partial_import_changed")
        error_text = str(exc)
        places_total = db.query(Place).filter(Place.city_id == city.id).count()
        job.last_error = error_text[:2000]
        job.finished_at = datetime.utcnow()
        job.step_details = {
            **dict(job.step_details or {}),
            "changed_place_ids": changed_place_ids,
            "has_changes": bool(changed_place_ids),
        }
        if places_total > 0:
            append_step_warning(job, job.current_step or "unknown", exc, extra={"recovered_as": "partial_success"})
            job.status = "partial_success"
            if changed_place_ids:
                city.launch_status = "review_required"
                city.is_active = False
            else:
                city.launch_status, city.is_active = original_city_state
        else:
            job.status = "failed"
            city.launch_status, city.is_active = original_city_state
            set_step(job, "error", detail={"error": error_text})
        db.commit()
        send_admin_alert(
            title="Import completed with warnings" if places_total > 0 else "Import pipeline failed",
            message=error_text[:1000],
            level="warning" if places_total > 0 else "error",
            city_slug=slug,
            job_id=int(job.id),
            details={
                "status": job.status,
                "source": job.source,
                "places_total": places_total,
                "changed_places": len(changed_place_ids),
            },
        )
        if places_total <= 0:
            raise
        return results


def _changed_places(db: Session, *, city_id: int, since: datetime) -> list[Place]:
    return (
        db.query(Place)
        .filter(Place.city_id == city_id, Place.updated_at >= since)
        .order_by(Place.id.asc())
        .all()
    )


def _notify_completion(
    *,
    city: City,
    job: CityAdminImportJob,
    places_total: int,
    changed_count: int,
    readiness: dict[str, Any],
    warnings: list[dict[str, object]],
) -> None:
    if changed_count:
        message = f"{city.name}: {changed_count} мест обновлено и отправлено на проверку."
    else:
        message = f"{city.name}: изменений нет, публикация сохранена."
    send_admin_alert(
        title="Import completed with warnings" if warnings else "Import pipeline finished",
        message=message,
        level="warning" if warnings else "info",
        city_slug=city.slug,
        job_id=int(job.id),
        details={
            "status": job.status,
            "source": job.source,
            "places_total": places_total,
            "changed_places": changed_count,
            "readiness": readiness,
            "warnings": warnings,
        },
    )


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
    log_import_event(
        db,
        event="import_step",
        city_slug=city_slug,
        actor_id=actor_id,
        message=f"{step}: {status}",
        details=payload,
    )
