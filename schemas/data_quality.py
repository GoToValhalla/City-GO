"""Admin data quality API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class DataQualityRefreshRequest(BaseModel):
    city_id: int | None = None
    limit: int | None = Field(default=None, ge=1, le=10_000)
    dry_run: bool = False


class DataQualityIssueListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class DataQualityBulkRequest(BaseModel):
    action_type: str
    filters: dict[str, Any] = Field(default_factory=dict)
    issue_ids: list[int] | None = None
    limit: int | None = Field(default=500, ge=1, le=10_000)
    confirm: bool = False
    reason: str | None = None
    preview_token: str | None = None


class DataQualityBulkResponse(BaseModel):
    action_type: str
    affected_count: int
    status: str | None = None
    created_candidates: int | None = None
    sample: list[dict[str, Any]] | None = None
    grouped_by_city: dict[str, int] | None = None
    grouped_by_category: dict[str, int] | None = None
    grouped_by_reason: dict[str, int] | None = None
    warnings: list[str] | None = None
    proposed_patch: dict[str, Any] | None = None
    preview_token: str | None = None


class DataQualityAutomationRequest(BaseModel):
    city_id: int | None = None
    city_slug: str | None = None
    limit: int | None = Field(default=500, ge=1, le=10_000)
    confirm: bool = False
    reason: str | None = None


class DataQualityAutomationRollbackRequest(BaseModel):
    candidate_ids: list[int] = Field(default_factory=list)
    confirm: bool = False
    reason: str | None = None


class DataQualityAutomationResponse(BaseModel):
    action_type: str
    affected_count: int
    status: str | None = None
    blocked_count: int | None = None
    candidate_ids: list[int] | None = None
    sample: list[dict[str, Any]] | None = None
    blocked_sample: list[dict[str, Any]] | None = None
    grouped_by_city: dict[str, int] | None = None
    grouped_by_category: dict[str, int] | None = None
    warnings: list[str] | None = None
    proposed_patch: dict[str, Any] | None = None
