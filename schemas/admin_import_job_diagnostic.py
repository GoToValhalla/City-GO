"""Diagnostic view of a single import job for mobile-first troubleshooting."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ImportJobTimelineEvent(BaseModel):
    timestamp: datetime
    severity: str
    type: str
    summary: str
    payload: dict[str, Any] | None = None


class ImportJobAttempt(BaseModel):
    attempt_number: int
    started_at: datetime
    ended_at: datetime | None = None
    result: str | None = None
    retry_count_at_claim: int | None = None


class ImportJobFailedStep(BaseModel):
    step_name: str
    step_label: str
    error_message: str | None = None
    finished_at: datetime | None = None


class ImportJobWorkflowOutcome(BaseModel):
    """A read-only reflection of the same fail-closed decision
    .github/workflows/run-import-worker-safe.yml makes from the worker's
    reported exit_code/stop_reason/oom_killed — never a new policy, and
    never persisted or acted on. `succeeded` is null when there is not yet
    enough reported data (e.g. exit_code missing) to evaluate the policy."""

    succeeded: bool | None = None
    reasons: list[str] = []


class ImportJobDiagnostic(BaseModel):
    job_id: int
    city_id: int
    city_slug: str
    city_name: str
    status: str
    current_step: str
    last_completed_step: str | None = None
    failure_reason: str | None = None
    partial_success_reason: str | None = None
    failed_steps: list[ImportJobFailedStep] = []
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    worker_state: str | None = None
    worker_run_id: str | None = None
    stop_reason: str | None = None
    stop_source: str | None = None
    exit_code: int | None = None
    oom_killed: bool | None = None
    workflow_name: str | None = None
    workflow_run_id: str | None = None
    workflow_run_url: str | None = None
    workflow_outcome: ImportJobWorkflowOutcome | None = None
    timeline: list[ImportJobTimelineEvent]
    attempts: list[ImportJobAttempt]
    diagnostic_report: str
