from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["safe", "medium", "dangerous"]
ReductionStatus = Literal["planned", "applied", "partial", "failed", "unsupported"]


class BacklogReductionAction(BaseModel):
    code: str
    title: str
    description: str
    queue_code: str
    reason_codes: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    enabled: bool
    disabled_reason: str | None = None
    dry_run_endpoint: str
    apply_endpoint: str
    requires_confirmation: bool
    max_batch_size: int
    owner: str
    expected_effect: str
    visible: bool = True
    affected_count: int = 0


class BacklogReductionPlan(BaseModel):
    generated_at: datetime
    summary: dict[str, int]
    actions: list[BacklogReductionAction]
    queues: list[dict[str, object]]


class BacklogReductionDryRunRequest(BaseModel):
    action_code: str
    queue_code: str | None = None
    reason_code: str | None = None
    city_id: int | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    include_samples: bool = True


class BacklogReductionApplyRequest(BacklogReductionDryRunRequest):
    confirmation_text: str


class BacklogReductionResult(BaseModel):
    action_code: str
    status: ReductionStatus
    dry_run: bool
    affected_count: int
    would_change_count: int = 0
    changed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    queued_count: int = 0
    unsupported_count: int = 0
    before_counts: dict[str, int] = Field(default_factory=dict)
    after_counts: dict[str, int] = Field(default_factory=dict)
    estimated_after_counts: dict[str, int] = Field(default_factory=dict)
    samples: list[dict[str, object]] = Field(default_factory=list)
    skipped_reasons: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    audit_id: int | None = None
    job_id: int | None = None
    limit: int
    message: str


class BacklogReductionJob(BaseModel):
    id: int
    action_code: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    requested_by: str
    dry_run: bool
    limit: int
    changed_count: int
    skipped_count: int
    failed_count: int
    queued_count: int
    result_json: dict[str, object]
