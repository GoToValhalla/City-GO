from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReviewItemRead(BaseModel):
    id: int
    place_id: int
    place_name: str
    source: str | None = None
    confidence: float | None = None
    status: str
    reason: str | None = None
    created_at: datetime
    place_version_at_creation: int


class ReviewDiffRead(ReviewItemRead):
    proposed_diff: dict[str, Any]


class ReviewMergeRequest(BaseModel):
    fields_to_apply: list[str] = Field(min_length=1)
    expected_version: int
    force_override_protected: bool = False


class ReviewRejectRequest(BaseModel):
    reason: str = Field(min_length=3)


class ManualOverrideRequest(BaseModel):
    field_name: str = Field(min_length=1)
    override_value: Any | None = None
    is_protected: bool = True


class TriggerEnrichRequest(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    source: str = "EXTERNAL_API_ENRICHED"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
