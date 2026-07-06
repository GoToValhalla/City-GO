"""Shared admin import job display resolution."""

from __future__ import annotations

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.import_pipeline.progress import is_stalled, step_label
from services.import_pipeline.steps import STEP_QUEUED

FAILED_IMPORT_STATUSES = {"failed", "stalled", "import_failed"}


def is_published_city(city: City) -> bool:
    return city.launch_status == "published" and bool(city.is_active)


def is_active_import_job(job: CityAdminImportJob | None) -> bool:
    return job is not None and job.status in {"queued", "running"}


def import_diff(job: CityAdminImportJob | None) -> dict[str, object]:
    if job is None:
        return {}
    details = dict(job.step_details or {})
    for key in ("import_diff", "import_summary"):
        value = details.get(key)
        if isinstance(value, dict):
            return value
    collecting = details.get("collecting_places")
    if isinstance(collecting, dict):
        nested = collecting.get("import_diff")
        if isinstance(nested, dict):
            return nested
    return {}


def pipeline_warnings(job: CityAdminImportJob | None) -> list[dict[str, object]]:
    if job is None:
        return []
    details = dict(job.step_details or {})
    raw = details.get("warnings")
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, dict)]


def job_execution_failed(job: CityAdminImportJob | None) -> bool:
    if job is None:
        return False
    if job.status in FAILED_IMPORT_STATUSES:
        return True
    if is_stalled(job):
        return True
    diff = import_diff(job)
    if str(diff.get("status") or "").lower() == "failed":
        return True
    details = dict(job.step_details or {})
    if details.get("stalled") is True:
        return True
    scopes_total = int(diff.get("scopes_total") or job.scopes_total or 0)
    scopes_ok = int(diff.get("scopes_succeeded") or job.scopes_succeeded or 0)
    if scopes_total > 0 and scopes_ok == 0 and str(diff.get("status") or "").lower() != "success":
        return True
    if pipeline_warnings(job) and scopes_total > 0 and scopes_ok == 0:
        return True
    return False


def effective_failed_items(job: CityAdminImportJob | None) -> int:
    if job is None:
        return 0
    base = int(job.failed_items or 0)
    if base > 0:
        return base
    warnings = pipeline_warnings(job)
    if warnings:
        return len(warnings)
    diff = import_diff(job)
    scopes_total = int(diff.get("scopes_total") or job.scopes_total or 0)
    scopes_ok = int(diff.get("scopes_succeeded") or job.scopes_succeeded or 0)
    if scopes_total > scopes_ok:
        return scopes_total - scopes_ok
    if str(diff.get("status") or "").lower() == "failed":
        return max(1, scopes_total)
    if job_execution_failed(job):
        return 1
    return 0


def import_error_summary(job: CityAdminImportJob | None) -> dict[str, object] | None:
    if job is None or not job_execution_failed(job):
        return None
    diff = import_diff(job)
    warnings = pipeline_warnings(job)
    first = warnings[0] if warnings else {}
    message = str(job.last_error or diff.get("last_error") or first.get("error") or "Import failed")
    return {
        "job_id": job.id,
        "failed_step": str(first.get("step") or job.current_step or "unknown"),
        "error_message": message,
        "import_status": str(diff.get("status") or job.status),
        "scopes_total": int(diff.get("scopes_total") or job.scopes_total or 0),
        "scopes_succeeded": int(diff.get("scopes_succeeded") or job.scopes_succeeded or 0),
    }


def import_execution_summary(
    job: CityAdminImportJob | None,
    *,
    places_published: int | None = None,
) -> dict[str, object]:
    diff = import_diff(job)
    scopes_total = int(diff.get("scopes_total") or (job.scopes_total if job else 0) or 0)
    scopes_ok = int(diff.get("scopes_succeeded") or (job.scopes_succeeded if job else 0) or 0)
    raw_found = diff.get("places_found")
    if raw_found is None and job is not None:
        raw_found = job.places_found
    raw_saved = diff.get("places_saved")
    if raw_saved is None and job is not None:
        raw_saved = job.places_saved
    summary: dict[str, object] = {
        "import_status": diff.get("status") or (job.status if job else None),
        "raw_collected": raw_found,
        "raw_saved": raw_saved,
        "deduplicated": diff.get("unchanged"),
        "published": places_published,
        "hidden": diff.get("hidden"),
        "rejected": diff.get("rejected"),
        "needs_review": diff.get("needs_review"),
        "scopes_total": scopes_total,
        "scopes_succeeded": scopes_ok,
        "scopes_failed": max(scopes_total - scopes_ok, 0) if scopes_total else None,
        "route_eligible": None,
    }
    warnings: list[str] = []
    if summary["route_eligible"] is None:
        warnings.append("ROUTE_ELIGIBLE_UNKNOWN")
    if not diff and job is not None:
        warnings.append("IMPORT_METRICS_PARTIAL")
    if warnings:
        summary["warnings"] = warnings
    return summary


def snapshot_warning(snapshot: dict[str, object] | None) -> dict[str, object] | None:
    if snapshot:
        return None
    return {
        "code": "SNAPSHOT_MISSING",
        "severity": "warning",
        "message": "Snapshot не создан. Нажмите «Обновить snapshot» для coverage и отчёта изменений.",
    }


def resolve_import_display(city: City, job: CityAdminImportJob | None) -> dict[str, object]:
    city_published = is_published_city(city)
    active_job = is_active_import_job(job)
    failed = job_execution_failed(job)
    raw_status = str(job.status if job is not None else city.launch_status)
    raw_step = str(job.current_step if job is not None else STEP_QUEUED)
    destination_publication_status = "published" if city_published else str(city.launch_status)
    job_execution_status = raw_status
    if failed and job is not None:
        display_status = raw_status
        display_step = raw_step
        display_step_label = step_label(raw_step)
        status_group = "failed"
    elif active_job:
        display_status = raw_status
        display_step = raw_step
        display_step_label = step_label(raw_step)
        status_group = "running" if raw_status == "running" else "queued"
    elif city_published and job is None:
        display_status = "published"
        display_step = "published"
        display_step_label = "Опубликован"
        status_group = "published"
    elif city_published and not failed:
        display_status = raw_status
        display_step = raw_step
        display_step_label = step_label(raw_step)
        status_group = "published" if city_published else "idle"
    else:
        display_status = raw_status
        display_step = raw_step
        display_step_label = step_label(raw_step)
        status_group = "failed" if raw_status in FAILED_IMPORT_STATUSES else "idle"
    return {
        "city_published": city_published,
        "active_job": active_job,
        "job_execution_failed": failed,
        "job_execution_status": job_execution_status,
        "destination_publication_status": destination_publication_status,
        "display_status": display_status,
        "display_step": display_step,
        "display_step_label": display_step_label,
        "status_group": status_group,
        "suppress_job_errors": city_published and not active_job and not failed,
    }
