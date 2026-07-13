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


class ImportJobDiagnostic(BaseModel):
    job_id: int
    city_id: int
    city_slug: str
    city_name: str
    status: str
    current_step: str
    last_completed_step: str | None = None
    failure_reason: str | None = None
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
