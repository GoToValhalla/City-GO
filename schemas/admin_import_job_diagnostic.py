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


class ImportJobStepBreakdown(BaseModel):
    """CITYGO-314: one row per persisted pipeline step (services/
    import_pipeline/progress.py::set_step -> ImportJobStep), read
    verbatim — never recomputed."""

    step_name: str
    step_label: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    counters: dict[str, Any] = {}
    error_message: str | None = None


class ImportJobFunnelAccounting(BaseModel):
    """CITYGO-315: whether the already-persisted funnel is internally
    consistent. `checked=False` means there was not enough data to verify
    (e.g. funnel unavailable) — distinct from `ok=True` (verified
    consistent) and `ok=False, checked=True` (verified inconsistent)."""

    ok: bool
    checked: bool
    reason: str | None = None
    requested_equation: dict[str, Any] = {}
    accepted_equation: dict[str, Any] = {}


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
    steps: list[ImportJobStepBreakdown] = []
    funnel: dict[str, Any] | None = None
    funnel_accounting: ImportJobFunnelAccounting | None = None
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
    timeline: list[ImportJobTimelineEvent]
    attempts: list[ImportJobAttempt]
    diagnostic_report: str
