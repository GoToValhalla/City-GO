"""Records import-worker lifecycle events reported by the safe-run workflow.

Reuses the existing SystemLog mechanism (write_system_log) — no new logging
system. Events are associated with a job only when job_id is explicitly
provided by the caller (i.e. only after the worker has actually claimed a
job); no job association is invented for pre-claim lifecycle events.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.system_log import SystemLog
from schemas.admin_worker_event import WORKER_LIFECYCLE_EVENTS, AdminWorkerEventRequest
from services.system_log_service import write_system_log

_MODULE = "import_worker"

_DEFAULT_MESSAGES: dict[str, str] = {
    "worker_run_started": "Import-worker run started",
    "worker_job_claimed": "Import-worker reports an active claimed job",
    "worker_health_check_failed": "Import-worker public health check degraded",
    "worker_stop_requested": "Import-worker stop requested",
    "worker_run_finished": "Import-worker run finished",
    "workflow_cleanup": "Import-worker workflow cleanup executed",
}


def record_worker_event(db: Session, *, payload: AdminWorkerEventRequest, actor_id: str) -> SystemLog:
    if payload.event not in WORKER_LIFECYCLE_EVENTS:
        raise ValueError(f"Unknown worker lifecycle event: {payload.event}")

    city_slug: str | None = None
    request_id: str | None = None
    if payload.job_id is not None:
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == payload.job_id).first()
        if job is not None:
            request_id = str(job.id)
            city = db.query(City).filter(City.id == job.city_id).first()
            city_slug = city.slug if city is not None else None

    details: dict[str, object] = {"event": payload.event}
    if payload.job_id is not None:
        details["job_id"] = payload.job_id
    if payload.worker_run_id is not None:
        details["worker_run_id"] = payload.worker_run_id
    if payload.stop_reason is not None:
        details["stop_reason"] = payload.stop_reason
    if payload.stop_source is not None:
        details["stop_source"] = payload.stop_source
    if payload.exit_code is not None:
        details["exit_code"] = payload.exit_code
    if payload.oom_killed is not None:
        details["oom_killed"] = payload.oom_killed
    if payload.workflow_name is not None:
        details["workflow_name"] = payload.workflow_name
    if payload.github_run_id is not None:
        details["github_run_id"] = payload.github_run_id
    if payload.github_run_url is not None:
        details["github_run_url"] = payload.github_run_url

    return write_system_log(
        db,
        level=payload.level,
        module=_MODULE,
        message=payload.message or _DEFAULT_MESSAGES.get(payload.event, payload.event),
        details=details,
        city_slug=city_slug,
        request_id=request_id,
        actor_id=actor_id,
        commit=True,
    )
