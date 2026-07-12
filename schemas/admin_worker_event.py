"""Structured import-worker lifecycle events reported by the safe-run workflow."""

from pydantic import BaseModel

WORKER_LIFECYCLE_EVENTS = frozenset(
    {
        "worker_run_started",
        "worker_job_claimed",
        "worker_health_check_failed",
        "worker_stop_requested",
        "worker_run_finished",
        "workflow_cleanup",
    }
)


class AdminWorkerEventRequest(BaseModel):
    event: str
    job_id: int | None = None
    message: str | None = None
    level: str = "info"
    worker_run_id: str | None = None
    stop_reason: str | None = None
    stop_source: str | None = None
    exit_code: int | None = None
    oom_killed: bool | None = None
    workflow_name: str | None = None
    github_run_id: str | None = None
    github_run_url: str | None = None


class AdminWorkerEventResponse(BaseModel):
    accepted: bool
    log_id: int | None = None
