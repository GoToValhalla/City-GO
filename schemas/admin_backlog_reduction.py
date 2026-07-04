from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="after")
    def normalize_summary_counts(self) -> "BacklogReductionPlan":
        totals = _queue_totals(self.queues)
        self.summary["route_blockers_reducible"] = _cap(self.summary.get("route_blockers_reducible"), totals.get("route_blockers", 0))
        self.summary["unknown_categories_auto_classifiable"] = _cap(self.summary.get("unknown_categories_auto_classifiable"), totals.get("route_unknown", 0))
        self.summary["manual_review_reclassifiable"] = _cap(self.summary.get("manual_review_reclassifiable"), totals.get("manual_review", 0))
        self.summary["total_manual_after_classification"] = _cap(self.summary.get("total_manual_after_classification"), totals.get("manual_review", 0))
        self.summary["verification_auto_recheckable"] = _cap(self.summary.get("verification_auto_recheckable"), totals.get("needs_verification", 0))
        content_total = totals.get("no_photo", 0) + totals.get("no_address", 0) + totals.get("no_description", 0)
        self.summary["content_enrichment_queueable"] = _cap(self.summary.get("content_enrichment_queueable"), content_total)
        auto_total = totals.get("auto_backlog", 0) + totals.get("needs_verification", 0) + totals.get("no_photo", 0) + totals.get("no_address", 0) + totals.get("no_description", 0) + totals.get("low_confidence", 0)
        self.summary["total_auto_fixable"] = _cap(self.summary.get("total_auto_fixable"), auto_total)
        return self


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

    @model_validator(mode="after")
    def normalize_dry_run_counts(self) -> "BacklogReductionResult":
        if self.dry_run and not self.would_change_count:
            self.would_change_count = int(self.changed_count or 0)
        return self


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


def _queue_totals(queues: list[dict[str, object]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for queue in queues:
        code = str(queue.get("code") or "")
        totals[code] = _to_int(queue.get("unique_places_count") or queue.get("total_count"))
    return totals


def _cap(value: object, maximum: int) -> int:
    return max(0, min(_to_int(value), max(0, int(maximum or 0))))


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
