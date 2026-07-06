from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PipelineMode = Literal["full", "import_only", "enrich_only", "membership_recalc_only"]


class DestinationPipelineRunRequest(BaseModel):
    scope_ids: list[int] | None = None
    mode: PipelineMode = "full"
    dry_run: bool = False
    idempotency_key: str | None = Field(default=None, max_length=255)


class DestinationPipelineRunRead(BaseModel):
    id: int
    destination_id: int
    destination_slug: str
    status: str
    stage: str
    mode: str
    dry_run: bool
    scope_ids: list[int]
    counters: dict[str, int]
    errors: list[dict[str, object]]
    message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    heartbeat_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DestinationPipelineRunResponse(BaseModel):
    run: DestinationPipelineRunRead
    message: str


class DestinationPipelineRunList(BaseModel):
    items: list[DestinationPipelineRunRead]
    total: int
    limit: int
    offset: int


class DestinationReadinessRead(BaseModel):
    destination_slug: str
    bootstrap_ready: bool = False
    bootstrap_blockers: list[str] = Field(default_factory=list)
    readiness_score: int
    places_total: int
    published_places: int
    route_eligible_places: int
    service_only_hidden: int
    orphan_places: int
    memberships_total: int
    pending_reviews: int
    address_coverage_pct: float
    photo_coverage_pct: float
    description_coverage_pct: float
    category_coverage_pct: float
    coordinates_coverage_pct: float
    opening_hours_coverage_pct: float
    completeness_score_avg: float
    degraded_sections: list[str]
    last_pipeline_run_status: str | None = None
    last_pipeline_run_at: datetime | None = None
