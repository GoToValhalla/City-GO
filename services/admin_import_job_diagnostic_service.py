"""Diagnostic snapshot for a single admin import job (mobile-first view).

Reuses existing entities only: CityAdminImportJob for job state, SystemLog
(via list_system_logs, filtered by module + request_id=job_id) for the
job-scoped timeline. No new logging system, no fake/synthetic data.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.system_log import SystemLog
from services.import_pipeline.steps import STEP_LABELS, TERMINAL_STEPS
from services.system_log_service import list_system_logs

TERMINAL_STATUSES = frozenset({"success", "success_with_warnings", "partial_success", "failed", "cancelled", "stalled"})

_IMPORT_WORKER_MODULE = "import_worker"
_CITY_IMPORT_MODULE = "city_import"

_EVENT_TYPE_MAP: dict[str, str] = {
    "worker_no_queued_jobs": "worker_idle",
    "worker_claim_skipped": "worker_idle",
    "worker_job_blocked_safe_mode": "resource_guard",
    "worker_job_claimed": "job_claimed",
    "worker_job_finished": "step_finished",
    "worker_job_failed": "failed",
    "worker_job_stalled": "stalled",
    "import_job_created": "queued",
    "import_job_started": "step_started",
    "unified_import_pipeline_finished": "step_finished",
    "address_enrichment_blocked": "resource_guard",
    "photo_enrichment_blocked": "resource_guard",
    "photo_enrichment_finished": "step_finished",
    "place_auto_repair_finished": "step_finished",
    "import_job_finished": "success",
    "import_job_failed": "failed",
    "import_job_cancelled": "cancelled",
    "worker_run_started": "worker_started",
    "worker_health_check_failed": "health_degradation",
    "worker_stop_requested": "sigterm",
    "worker_run_finished": "worker_finished",
    "workflow_cleanup": "workflow_cleanup",
}

_EVENT_SEVERITY_OVERRIDE: dict[str, str] = {
    "worker_job_blocked_safe_mode": "warning",
    "worker_job_failed": "error",
    "worker_job_stalled": "error",
    "import_job_failed": "error",
    "import_job_cancelled": "warning",
    "worker_health_check_failed": "warning",
    "worker_stop_requested": "warning",
}

# Populated by the workflow-reported worker lifecycle events (see
# services/admin_worker_event_service.py). Read in reverse-chronological
# order (most recent first) so the latest value wins for a job that has
# been claimed across more than one worker run.
_WORKER_LIFECYCLE_EVENTS = frozenset(
    {"worker_run_started", "worker_health_check_failed", "worker_stop_requested", "worker_run_finished", "workflow_cleanup"}
)


def _timeline_event_from_log(row: SystemLog) -> dict[str, object]:
    details = dict(row.details or {})
    event = str(details.pop("event", row.message))
    event_type = _EVENT_TYPE_MAP.get(event, event)
    severity = _EVENT_SEVERITY_OVERRIDE.get(event, row.level or "info")
    return {
        "timestamp": row.created_at,
        "severity": severity,
        "type": event_type,
        "summary": row.message,
        "payload": details or None,
    }


def _job_logs(db: Session, *, job_id: int) -> list[SystemLog]:
    worker_logs, _ = list_system_logs(db, module=_IMPORT_WORKER_MODULE, request_id=str(job_id), sort="asc", limit=200)
    import_logs, _ = list_system_logs(db, module=_CITY_IMPORT_MODULE, request_id=str(job_id), sort="asc", limit=200)
    combined = list(worker_logs) + list(import_logs)
    combined.sort(key=lambda row: (row.created_at or datetime.min, row.id))
    return combined


def _job_timeline(logs: list[SystemLog]) -> list[dict[str, object]]:
    return [_timeline_event_from_log(row) for row in logs]


def _worker_lifecycle_fields(logs: list[SystemLog]) -> dict[str, object | None]:
    """Latest known value per field across this job's worker lifecycle
    events, in chronological order — the most recent reported value wins
    (e.g. a worker started/stopped more than once for the same job)."""
    fields: dict[str, object | None] = {
        "worker_state": None,
        "worker_run_id": None,
        "stop_reason": None,
        "stop_source": None,
        "exit_code": None,
        "oom_killed": None,
        "workflow_name": None,
        "workflow_run_id": None,
        "workflow_run_url": None,
    }
    for row in logs:
        details = row.details or {}
        event = str(details.get("event") or "")
        if event not in _WORKER_LIFECYCLE_EVENTS:
            continue
        if event == "worker_run_started":
            fields["worker_state"] = "running"
        elif event == "worker_stop_requested":
            fields["worker_state"] = "stopped"
        elif event == "worker_run_finished":
            fields["worker_state"] = "finished"
        if "worker_run_id" in details:
            fields["worker_run_id"] = details["worker_run_id"]
        if "stop_reason" in details:
            fields["stop_reason"] = details["stop_reason"]
        if "stop_source" in details:
            fields["stop_source"] = details["stop_source"]
        if "exit_code" in details:
            fields["exit_code"] = details["exit_code"]
        if "oom_killed" in details:
            fields["oom_killed"] = details["oom_killed"]
        if "workflow_name" in details:
            fields["workflow_name"] = details["workflow_name"]
        if "github_run_id" in details:
            fields["workflow_run_id"] = details["github_run_id"]
        if "github_run_url" in details:
            fields["workflow_run_url"] = details["github_run_url"]
    return fields


def _last_completed_step(job: CityAdminImportJob) -> str | None:
    if job.current_step in TERMINAL_STEPS or job.status in TERMINAL_STATUSES:
        return job.current_step
    return None


def _duration_seconds(job: CityAdminImportJob) -> int | None:
    if job.started_at is None:
        return None
    end = job.finished_at or datetime.utcnow()
    return max(0, int((end - job.started_at).total_seconds()))


def _step_label(step: str | None) -> str:
    if step is None:
        return "—"
    return STEP_LABELS.get(step, step)


def _build_report_text(
    *,
    job: CityAdminImportJob,
    city: City,
    last_completed_step: str | None,
    duration_seconds: int | None,
    timeline: list[dict[str, object]],
    worker_fields: dict[str, object | None],
) -> str:
    lines = [
        "CITY GO — Import Job Diagnostic Report",
        f"Job #{job.id} — {city.name} ({city.slug})",
        f"Status: {job.status}",
        f"Current step: {_step_label(job.current_step)}",
    ]
    if last_completed_step is not None:
        lines.append(f"Last completed step: {_step_label(last_completed_step)}")
    if job.last_error:
        lines.append(f"Failure reason: {job.last_error}")
    lines.append(f"Started at: {job.started_at.isoformat() if job.started_at else 'not started'}")
    lines.append(f"Finished at: {job.finished_at.isoformat() if job.finished_at else 'not finished'}")
    if duration_seconds is not None:
        lines.append(f"Duration: {duration_seconds}s")
    lines.append(f"Source: {job.source}")
    lines.append(f"Scopes: {job.scopes_succeeded}/{job.scopes_total}")
    lines.append(f"Places: found={job.places_found}, saved={job.places_saved}")

    if worker_fields.get("worker_state") is not None:
        lines.append(f"Worker state: {worker_fields['worker_state']}")
    if worker_fields.get("worker_run_id") is not None:
        lines.append(f"Worker run ID: {worker_fields['worker_run_id']}")
    if worker_fields.get("stop_reason") is not None:
        stop_line = f"Stop reason: {worker_fields['stop_reason']}"
        if worker_fields.get("stop_source") is not None:
            stop_line += f" (source: {worker_fields['stop_source']})"
        lines.append(stop_line)
    if worker_fields.get("exit_code") is not None:
        lines.append(f"Exit code: {worker_fields['exit_code']}")
    if worker_fields.get("oom_killed") is not None:
        lines.append(f"OOM killed: {worker_fields['oom_killed']}")
    if worker_fields.get("workflow_run_url") is not None:
        workflow_line = f"Workflow: {worker_fields.get('workflow_name') or 'GitHub Actions'} — {worker_fields['workflow_run_url']}"
        lines.append(workflow_line)

    if timeline:
        lines.append("")
        lines.append(f"Timeline ({len(timeline)} events):")
        for event in timeline:
            ts = event["timestamp"]
            ts_text = ts.isoformat() if isinstance(ts, datetime) else str(ts)
            lines.append(f"- [{ts_text}] {event['severity']}/{event['type']}: {event['summary']}")

    return "\n".join(lines)


def build_import_job_diagnostic(db: Session, *, job_id: int) -> dict[str, object] | None:
    job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job is None:
        return None
    city = db.query(City).filter(City.id == job.city_id).first()
    if city is None:
        return None

    logs = _job_logs(db, job_id=job_id)
    timeline = _job_timeline(logs)
    worker_fields = _worker_lifecycle_fields(logs)
    last_completed_step = _last_completed_step(job)
    duration_seconds = _duration_seconds(job)

    report = _build_report_text(
        job=job,
        city=city,
        last_completed_step=last_completed_step,
        duration_seconds=duration_seconds,
        timeline=timeline,
        worker_fields=worker_fields,
    )

    return {
        "job_id": job.id,
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "status": job.status,
        "current_step": job.current_step,
        "last_completed_step": last_completed_step,
        "failure_reason": job.last_error,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "duration_seconds": duration_seconds,
        "worker_state": worker_fields["worker_state"],
        "worker_run_id": worker_fields["worker_run_id"],
        "stop_reason": worker_fields["stop_reason"],
        "stop_source": worker_fields["stop_source"],
        "exit_code": worker_fields["exit_code"],
        "oom_killed": worker_fields["oom_killed"],
        "workflow_name": worker_fields["workflow_name"],
        "workflow_run_id": worker_fields["workflow_run_id"],
        "workflow_run_url": worker_fields["workflow_run_url"],
        "timeline": timeline,
        "diagnostic_report": report,
    }
