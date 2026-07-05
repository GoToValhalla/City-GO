"""Сборка read-only статуса Data Pipeline Control Plane."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from schemas.data_pipeline_status import DataPipelineStatusResponse
from services.data_pipeline_status.constants import SECTION_LABELS
from services.data_pipeline_status.metrics import build_pipeline_metrics
from services.data_pipeline_status.queues import build_pipeline_queues
from services.data_pipeline_status.recent_runs import build_recent_runs


def build_data_pipeline_status(db: Session) -> DataPipelineStatusResponse:
    metrics = build_pipeline_metrics(db)
    queues = build_pipeline_queues(db)
    degraded = _degraded_sections(metrics, queues)
    overall = _overall_status(metrics, degraded)
    return DataPipelineStatusResponse(
        overall_status=overall,
        degraded_sections=degraded,
        metrics=metrics,
        queues=queues,
        recent_runs=build_recent_runs(db),
        fetched_at=datetime.utcnow(),
    )


def _degraded_sections(metrics, queues) -> list[str]:
    sections: list[str] = []
    if any(row.code == "import" and row.status in {"error", "warning"} for row in queues):
        sections.append(SECTION_LABELS["imports"])
    if any(row.code == "enrichment" and row.status in {"error", "warning"} for row in queues):
        sections.append(SECTION_LABELS["enrichment"])
    if metrics.pending_photos > 0 or any(row.code == "photo_review" and row.pending_count > 0 for row in queues):
        sections.append(SECTION_LABELS["photos"])
    if metrics.open_review_items > 0:
        sections.append(SECTION_LABELS["verification"])
    if metrics.places_without_coordinates > 0:
        sections.append(SECTION_LABELS["coordinates"])
    return sections


def _overall_status(metrics, degraded: list[str]) -> str:
    if metrics.places_total == 0 and not degraded:
        return "empty"
    if len(degraded) >= 3:
        return "full_degraded"
    if degraded:
        return "partial_degraded"
    return "healthy"
