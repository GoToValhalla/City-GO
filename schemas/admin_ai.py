"""Schemas for controlled admin AI selector."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AIProviderRead(BaseModel):
    key: str
    label: str
    model_name: str
    input_usd_per_1m: float
    output_usd_per_1m: float
    max_output_tokens: int
    enabled: bool
    disabled_reason: str | None = None


class AITaskRead(BaseModel):
    key: str
    label: str
    description: str
    mode: str
    schema_version: str
    enabled: bool
    allowed_provider_keys: list[str]
    max_batch_size: int
    writes_public_fields: bool
    disabled_reason: str | None = None


class AIEstimateRequest(BaseModel):
    task_type: str
    provider_key: str
    review_queue_item_id: int | None = None
    place_id: int | None = None


class AIEstimateResponse(BaseModel):
    task_type: str
    provider_key: str
    model_name: str
    schema_version: str
    input_tokens_estimate: int
    output_tokens_limit: int
    estimated_cost_usd: float
    writes_public_fields: bool


class AITaskRunRequest(AIEstimateRequest):
    confirm_estimate: bool = False


class AITaskRunRead(BaseModel):
    id: int
    task_type: str
    provider_key: str
    model_name: str
    mode: str
    status: str
    schema_version: str
    actor: str
    city_id: int | None = None
    place_id: int | None = None
    review_queue_item_id: int | None = None
    input_tokens_estimate: int
    output_tokens_limit: int
    estimated_cost_usd: float
    actual_cost_usd: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class AICandidateRead(BaseModel):
    id: int
    task_run_id: int
    city_id: int | None = None
    place_id: int | None = None
    review_queue_item_id: int | None = None
    candidate_type: str
    status: str
    proposed_payload: dict[str, Any]
    evidence_payload: dict[str, Any] | None = None
    confidence_score: float | None = None
    created_by: str
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AITaskRunDetailRead(AITaskRunRead):
    candidates: list[AICandidateRead] = Field(default_factory=list)


class AICandidateResolveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)
