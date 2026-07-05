"""Схемы read-only Data Pipeline Control Plane v1.2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PipelineOverallStatus = Literal["healthy", "partial_degraded", "full_degraded", "empty"]
QueueHealthStatus = Literal["ok", "warning", "error", "idle"]


class DataPipelineQueueRow(BaseModel):
    code: str
    label: str
    pending_count: int = 0
    running_count: int = 0
    failed_count: int = 0
    status: QueueHealthStatus = "idle"
    updated_at: datetime | None = None


class DataPipelineRecentRun(BaseModel):
    run_id: int
    run_type: str
    run_type_label: str
    city_slug: str | None = None
    city_name: str | None = None
    status: str
    status_label: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    error_summary: str | None = None


class DataPipelineMetrics(BaseModel):
    places_total: int = 0
    places_without_coordinates: int = 0
    places_route_eligible: int = 0
    open_review_items: int = 0
    pending_photos: int = 0
    active_import_jobs: int = 0
    active_enrichment_tasks: int = 0


class DataPipelineStatusResponse(BaseModel):
    overall_status: PipelineOverallStatus
    degraded_sections: list[str] = Field(default_factory=list)
    metrics: DataPipelineMetrics
    queues: list[DataPipelineQueueRow]
    recent_runs: list[DataPipelineRecentRun] = Field(default_factory=list)
    fetched_at: datetime
