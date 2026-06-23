"""Schemas for automated import/enrichment pipeline foundation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineRunResponse(BaseModel):
    job_id: int
    city_slug: str
    status: str
    counters: dict[str, int] = Field(default_factory=dict)
    message: str | None = None


class ImportJobStepRead(BaseModel):
    id: int
    job_id: int
    step_name: str
    status: str
    counters: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class FieldConfidenceRead(BaseModel):
    field_name: str
    confidence: float
    confidence_level: str
    source_type: str
    freshness_status: str
    conflict_status: str
    is_manual_verified: bool

    model_config = {"from_attributes": True}


class ReviewQueueRead(BaseModel):
    id: int
    city_id: int
    place_id: int
    field_name: str
    reason: str
    severity: str
    status: str
    payload: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResolveReviewRequest(BaseModel):
    resolution: str = "resolved"


class PhotoCandidateActionResponse(BaseModel):
    id: int
    place_id: int
    status: str
    is_primary_candidate: bool

    model_config = {"from_attributes": True}
