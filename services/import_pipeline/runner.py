"""Оркестратор pipeline: импорт → адреса → фото → качество → readiness."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup  # noqa: F401 — kept as compat symbol; replaced by normalize_places_categories, see STEP_COMPUTING_QUALITY below
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.admin_city_import_runner import run_osm_import_only, summarize_import_results
from services.admin_import_job_change_service import record_place_changes
from services.category_normalize_service import normalize_city_categories, normalize_places_categories  # noqa: F401 — normalize_city_categories kept as compat symbol; runner uses normalize_places_categories on the already-fetched places list
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.progress import append_step_warning, set_step
from services.import_pipeline.scope_errors import classify_scope_error
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
from services.import_pipeline.transaction import (
    is_aborted_transaction_error,
    record_step_isolation,
    recover_after_db_error,
    rollback_session,
    transaction_is_aborted,
)
from services.import_pipeline.schema_compat import collecting_has_schema_failure, diagnose_import_schema_gaps, ensure_import_pipeline_schema, is_schema_mismatch_error
from services.photo_enrichment_diagnostics import build_photo_enrichment_diagnostics
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
    city_id = int(city.id)
    job_id = int(job.id)
    original = (city.launch_status, bool(city.is_active))
    started = datetime.utcnow()
    warnings: list[dict[str, object]] = []
    results: dict[str, object] = {}
    job.status = "running"
    job.started_at = job.started_at or started
    set_step(job, STEP_RUNNING)
    db.commit()
    try:
        gaps = diagnose_import_schema_gaps(db.connection())
        if any(gaps.values()):
            repair = ensure_import_pipeline_schema(db.get_bind().engine)
            warnings.append({"step": "schema_preflight", "status": "repaired", "before": gaps, **repair})
        set_step(job, STEP_COLLECTING_PLACES)
        _log(db, job, city.slug, actor_id, STEP_COLLECTING_PLACES, "started")
        _touch_job(job)
        db.commit()
        summary = summarize_import_results(
            run_osm_import_only(city.slug, force=force, city_admin_import_job_id=int(job.id))
        )
        results["import"] = summary
        job.scopes_succeeded = int(summary.get("scopes_succeeded") or 0)
        job.places_found = int(summary.get("places_found") or 0)
        job.places_saved = int(summary.get("places_saved") or 0)
        collecting_failed = str(summary.get("status") or "").lower() != "success"
        schema_collecting_failed_any_scope = collecting_failed and collecting_has_schema_failure(summary)
        if collecting_failed:
            isolation = record_step_isolation(
                db,
                job,
                after_step=STEP_COLLECTING_PLACES,
                reason="collecting_places_failed",
                dependency=STEP_COLLECTING_PLACES,
            )
            if isolation["status"] == "rolled_back":
                warnings.append(isolation)
                results["transaction_isolation"] = isolation
                job = _reload_after_rollback(db, CityAdminImportJob, job_id, job)
        try:
            total = db.query(Place).filter(Place.city_id == city_id).count()
        except SQLAlchemyError as exc:
            isolation = recover_after_db_error(db, job, step=STEP_COLLECTING_PLACES, error=exc)
            warnings.append({**isolation, "error": str(exc)[:1000]})
            results["transaction_isolation"] = isolation
            if isolation.get("rolled_back") or isolation.get("status") == "rolled_back":
                job = _reload_after_rollback(db, CityAdminImportJob, job_id, job)
            total = db.query(Place).filter(Place.city_id == city_id).count()
        set_step(
            job,
            STEP_COLLECTING_PLACES,
            total=total,
            processed=total,
            successful=job.places_saved,
            detail={"import_diff": summary},
        )
        db.commit()
        # A schema error in one scope must not block finding_images when other
        # scopes in this same run already succeeded and produced real places —
        # only a schema failure with zero successful scopes this run is a true
        # blocker (matches collecting_failed's own "status != success" check,
        # which already treats partial_success/failed uniformly as "not clean").
        scopes_succeeded_this_run = int(summary.get("scopes_succeeded") or 0)
        schema_collecting_failed = schema_collecting_failed_any_scope and scopes_succeeded_this_run <= 0
        if collecting_failed and total <= 0:
            raise RuntimeError(str(summary.get("last_error") or "Ошибка импорта OSM"))
        if collecting_failed:
            warning = {
                "step": STEP_COLLECTING_PLACES,
                "error": str(summary.get("last_error") or "partial import"),
                "kind": "schema_mismatch" if schema_collecting_failed_any_scope else "scope_failure",
            }
            warnings.append(warning)
            append_step_warning(job, STEP_COLLECTING_PLACES, warning["error"])
        addresses = _optional_step(
            db,
            job,
            city.slug,
            actor_id,
            STEP_FINDING_ADDRESSES,
            warnings,
            lambda: run_address_backfill(["--city", city.slug, "--limit", str(ADDRESS_LIMIT), "--apply"]),
        )
        results["addresses"] = addresses
        set_step(
            job,
            STEP_FINDING_ADDRESSES,
            processed=int(addresses.get("checked") or 0),
            successful=int(addresses.get("updated") or 0),
            failed=int(addresses.get("errors") or 0),
        )
        db.commit()
        images = _optional_step(
            db,
            job,
            city.slug,
            actor_id,
            STEP_FINDING_IMAGES,
            warnings,
            lambda: run_image_enrich(["--city", city.slug, "--limit", str(IMAGE_LIMIT), "--apply"]),
            skip_if_dependency_failed=schema_collecting_failed,
            dependency_step=STEP_COLLECTING_PLACES,
        )
        image_result = images if isinstance(images, dict) else {}
        try:
            photo_diagnostics = build_photo_enrichment_diagnostics(
                db,
                city,
                enrichment_result=image_result if image_result.get("status") != "skipped" else None,
                step_status=str(image_result.get("status") or "") or None,
                dependency_step=str(image_result.get("dependency") or "") or None,
                scan_limit=IMAGE_LIMIT,
            )
        except SQLAlchemyError as exc:
            recovery = recover_after_db_error(db, job, step=STEP_FINDING_IMAGES, error=exc)
            warnings.append({**recovery, "step": STEP_FINDING_IMAGES})
            if recovery.get("rolled_back"):
                job = _reload_after_rollback(db, CityAdminImportJob, job_id, job)
            photo_diagnostics = {
                "step_status": "failed",
                "provider_error": str(exc)[:1000],
                "provider_status": "diagnostics_failed",
                "admin_hint": "Диагностика фото недоступна из-за ошибки БД после collecting_places.",
            }
        results["images"] = {**image_result, "photo_diagnostics": photo_diagnostics}
        results["photo_diagnostics"] = photo_diagnostics
        job.step_details = {**dict(job.step_details or {}), "photo_diagnostics": photo_diagnostics, "photo_enrichment": results["images"]}
        set_step(
            job,
            STEP_FINDING_IMAGES,
            processed=int(images.get("scanned_places") or 0),
            successful=int(images.get("created") or 0),
            failed=int(images.get("failed_image_lookup") or images.get("failed") or 0),
        )
        db.commit()
        db.expire_all()
        places = _changed(db, city_id, started)
        for place in places:
            mark_place_for_review(place, reason="import_or_enrichment_changed")
        db.commit()
        set_step(job, STEP_PREPARING_DESCRIPTIONS, detail={"mode": "manual_required"})
        cats = normalize_places_categories(db, places=places, apply=True, job_id=int(job.id))
        results["categories"] = cats
        set_step(job, STEP_CATEGORIES_TAGS, processed=int(cats.get("scanned") or 0), successful=int(cats.get("updated") or 0))
        db.commit()
        ids = sorted({int(p.id) for p in places})
        record_place_changes(db, job=job, places=places, since=started)
        results.update(
            changed_place_ids=ids,
            has_changes=bool(ids),
            quality={"mode": "foundation", "changed_places": len(ids)},
        )
        set_step(job, STEP_COMPUTING_QUALITY, processed=len(ids), detail=results["quality"])
        set_step(job, STEP_COMPUTING_READINESS)
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}
        results["readiness"] = readiness
        set_step(job, STEP_COMPUTING_READINESS, detail={"readiness_score": readiness.get("readiness_score")})
        if total <= 0:
            raise RuntimeError("OSM import finished without places")
        set_step(job, STEP_READY_FOR_REVIEW, successful=len(ids), processed=len(ids))
        job.finished_at = datetime.utcnow()
        job.step_details = {
            **dict(job.step_details or {}),
            "warnings": warnings,
            "changed_place_ids": ids,
            "has_changes": bool(ids),
            "import_summary": summary,
        }
        if _job_recovered_externally(db, job_id):
            log_import_event(
                db,
                event="import_pipeline_finished_after_recovery",
                city_slug=city.slug,
                actor_id=actor_id,
                message=f"Pipeline #{job.id}: finished after job was already marked recovered externally; not overwriting status",
                details={"job_id": job.id},
            )
            db.commit()
            return results
        _finalize_import_status(job, summary=summary, total=total, warnings=warnings)
        if original[0] == "importing":
            city.launch_status = "review_required"
            city.is_active = False
        else:
            city.launch_status, city.is_active = original
        city.last_import_at = job.finished_at
        _try_refresh_snapshot(db, city_id=city_id, source="import_pipeline_finished")
        log_import_event(
            db,
            event="import_pipeline_finished",
            city_slug=city.slug,
            actor_id=actor_id,
            message=f"Pipeline #{job.id}: {len(ids)} изменений",
            details={"job_id": job.id, **results},
        )
        db.commit()
        if notify_completion:
            _notify(city, job, total, len(ids), readiness, warnings)
        return results
    except Exception as exc:
        failed_step = job.current_step or "unknown"
        if is_aborted_transaction_error(exc) or isinstance(exc, SQLAlchemyError) or transaction_is_aborted(db):
            rollback_session(db)
            job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).one()
            city = db.query(City).filter(City.id == city_id).one()
        places = _changed(db, city_id, started)
        ids = sorted({int(p.id) for p in places})
        record_place_changes(db, job=job, places=places, since=started)
        for place in places:
            mark_place_for_review(place, reason="partial_import_changed")
        total = db.query(Place).filter(Place.city_id == city_id).count()
        detail = {"step": failed_step, "error": str(exc)[:1000], "places_total": total}
        results["partial_success_after_error"] = detail
        job.finished_at = datetime.utcnow()
        job.step_details = {
            **dict(job.step_details or {}),
            "changed_place_ids": ids,
            "has_changes": bool(ids),
            "partial_success_after_error": detail,
            "warnings": warnings,
        }
        if _job_recovered_externally(db, job_id):
            log_import_event(
                db,
                event="import_pipeline_failed_after_recovery",
                city_slug=city.slug,
                actor_id=actor_id,
                message=f"Pipeline #{job.id}: failed after job was already marked recovered externally; not overwriting status",
                details={"job_id": job.id, "error": str(exc)[:1000]},
            )
            db.commit()
            if total <= 0:
                raise
            return results
        job.last_error = str(exc)[:2000]
        if total > 0:
            job.status = "partial_success"
            set_step(job, STEP_READY_FOR_REVIEW, total=total, processed=total, successful=total, detail={"partial_success_after_error": detail})
            if original[0] == "importing":
                city.launch_status = "review_required"
                city.is_active = False
            else:
                city.launch_status, city.is_active = original
        else:
            job.status = "failed"
            city.launch_status, city.is_active = original
        error_meta = classify_scope_error(str(exc))
        log_import_event(
            db,
            event="import_pipeline_failed",
            city_slug=city.slug,
            actor_id=actor_id,
            level="error",
            message=f"Pipeline #{job.id} failed at {failed_step}: {str(exc)[:500]}",
            details={"job_id": job.id, "city_id": city_id, "step": failed_step, "error": str(exc)[:1000], "places_total": total, **error_meta},
        )
        _try_refresh_snapshot(db, city_id=city_id, source="import_pipeline_partial_failure")
        db.commit()
        if notify_completion:
            send_admin_alert(
                title="Import completed with warnings",
                message=f"{city.name}: pipeline завершён с ошибкой, изменения оставлены на проверке.",
                level="warning",
                city_slug=city.slug,
                job_id=int(job.id),
                details={"status": job.status, "places_total": total, "changed_places": len(ids), "warnings": warnings + [detail]},
            )
        if total <= 0:
            raise
        return results


def _touch_job(job: CityAdminImportJob) -> None:
    job.updated_at = datetime.utcnow()


RECOVERED_STATUSES = frozenset({"stalled", "cancelled"})


def _job_recovered_externally(db: Session, job_id: int) -> bool:
    """True if an admin/orphan-cleanup action already terminated this job
    (marked stalled or cancelled) while this pipeline run was still executing.

    Checked against the DB's committed status, not the in-memory `job` object,
    since that object can be stale relative to a concurrent admin request.
    """
    current_status = db.query(CityAdminImportJob.status).filter(CityAdminImportJob.id == job_id).scalar()
    return current_status in RECOVERED_STATUSES


def _reload_after_rollback(db: Session, model: type, obj_id: int, fallback: Any) -> Any:
    """Re-fetch after a rollback that may have expired/deleted the ORM instance.

    ponytail: test sqlite fixture commits aren't isolated from later rollback (no SAVEPOINT),
    so the row can briefly appear gone in tests only; on Postgres the row is always found.
    """
    reloaded = db.get(model, obj_id)
    return reloaded if reloaded is not None else fallback


def _try_refresh_snapshot(db: Session, *, city_id: int, source: str) -> None:
    try:
        if transaction_is_aborted(db):
            rollback_session(db)
        from services.admin_city_import_job_payload import refresh_import_job_snapshot

        refresh_import_job_snapshot(db, city_id=city_id, source=source)
    except Exception:
        if transaction_is_aborted(db):
            rollback_session(db)


def _finalize_import_status(
    job: CityAdminImportJob,
    *,
    summary: dict[str, object],
    total: int,
    warnings: list[dict[str, object]],
) -> None:
    scopes_total = int(summary.get("scopes_total") or 0)
    scopes_ok = int(summary.get("scopes_succeeded") or 0)
    if scopes_total > 0 and scopes_ok == 0 and str(summary.get("status") or "").lower() == "failed":
        job.status = "partial_success" if total > 0 else "failed"
        job.last_error = job.last_error or str(summary.get("last_error") or "All import scopes failed")
    elif warnings:
        job.status = "success_with_warnings"
    else:
        job.status = "success"


def _changed(db: Session, city_id: int, since: datetime) -> list[Place]:
    return db.query(Place).filter(Place.city_id == city_id, Place.updated_at >= since).order_by(Place.id).all()


def _notify(city: City, job: CityAdminImportJob, total: int, changed: int, readiness: dict[str, object], warnings: list[dict[str, object]]) -> None:
    send_admin_alert(
        title="Import completed with warnings" if warnings else "Import pipeline finished",
        message=f"{city.name}: {changed} мест обновлено и отправлено на проверку." if changed else f"{city.name}: изменений нет, публикация сохранена.",
        level="warning" if warnings else "info",
        city_slug=city.slug,
        job_id=int(job.id),
        details={"status": job.status, "places_total": total, "changed_places": changed, "readiness": readiness, "warnings": warnings},
    )


def _optional_step(
    db: Session,
    job: CityAdminImportJob,
    slug: str,
    actor: str,
    step: str,
    warnings: list[dict[str, object]],
    action: Callable[[], object],
    *,
    skip_if_dependency_failed: bool = False,
    dependency_step: str | None = None,
) -> dict[str, object]:
    if skip_if_dependency_failed:
        skipped = {
            "step": step,
            "status": "skipped",
            "reason": "dependency_failed",
            "dependency": dependency_step or STEP_COLLECTING_PLACES,
        }
        warnings.append(skipped)
        set_step(job, step, detail=skipped)
        return skipped
    set_step(job, step)
    try:
        _log(db, job, slug, actor, step, "started")
        db.commit()
    except SQLAlchemyError as exc:
        recovery = recover_after_db_error(db, job, step=step, error=exc)
        warnings.append({**recovery, "error": str(exc)[:1000]})
        return {"status": "failed", "error": str(exc)[:1000], "transaction_isolation": recovery}
    try:
        result = action()
        _log(db, job, slug, actor, step, "success")
        return result if isinstance(result, dict) else {"result": result}
    except SQLAlchemyError as exc:
        recovery = recover_after_db_error(db, job, step=step, error=exc)
        payload = {"status": "failed", "error": str(exc)[:1000], "transaction_isolation": recovery}
        warnings.append({**payload, "step": step})
        append_step_warning(job, step, exc)
        _safe_log_warning(db, job, slug, actor, step, exc)
        return payload
    except Exception as exc:
        recovery = (
            recover_after_db_error(db, job, step=step, error=exc)
            if isinstance(exc, SQLAlchemyError) or is_aborted_transaction_error(exc)
            else None
        )
        payload: dict[str, object] = {
            "status": "warning" if not is_aborted_transaction_error(exc) else "failed",
            "error": str(exc)[:1000],
        }
        if recovery is not None:
            payload["transaction_isolation"] = recovery
            warnings.append(recovery)
        warnings.append({"step": step, **payload})
        append_step_warning(job, step, exc)
        _safe_log_warning(db, job, slug, actor, step, exc)
        return payload


def _safe_log_warning(db: Session, job: CityAdminImportJob, slug: str, actor: str, step: str, exc: Exception) -> None:
    try:
        if transaction_is_aborted(db):
            rollback_session(db)
        _log(db, job, slug, actor, step, "warning", error=str(exc))
        db.commit()
    except SQLAlchemyError:
        rollback_session(db)


def _log(db: Session, job: CityAdminImportJob, slug: str, actor: str, step: str, status: str, **details: object) -> None:
    payload = {"city_slug": slug, "job_id": job.id, "step": step, "status": status, **details}
    print(json.dumps(payload, ensure_ascii=False, default=str))
    log_import_event(
        db,
        event="import_step",
        city_slug=slug,
        actor_id=actor,
        message=f"{step}: {status}",
        details=payload,
    )
