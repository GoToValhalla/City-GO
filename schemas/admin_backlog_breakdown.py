from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminBacklogSummary(BaseModel):
    unique_problem_places: int
    total_problem_signals: int
    route_blocker_places: int
    auto_fixable_places: int
    manual_places: int
    verification_backlog_places: int
    content_gap_places: int


class AdminBacklogReasonBreakdown(BaseModel):
    code: str
    title: str
    count: int
    auto_fixable: bool
    manual_required: bool
    sample_endpoint: str | None = None


class AdminBacklogQueueBreakdown(BaseModel):
    code: str
    title: str
    total_count: int
    unique_places_count: int
    total_problem_signals: int
    auto_fixable_count: int
    manual_count: int
    overlap_count: int
    recommended_action: str
    severity: str
    sample_endpoint: str | None = None
    reasons: list[AdminBacklogReasonBreakdown]


class AdminBacklogOverlap(BaseModel):
    left: str
    right: str
    count: int


class AdminBacklogBreakdownResponse(BaseModel):
    generated_at: datetime
    summary: AdminBacklogSummary
    queues: list[AdminBacklogQueueBreakdown]
    overlaps: list[AdminBacklogOverlap]
