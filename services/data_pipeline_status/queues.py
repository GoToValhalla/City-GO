"""Канонические очереди Data Pipeline."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import EnrichmentTask
from models.place_image import PlaceImage
from models.review_queue_item import ReviewQueueItem
from schemas.data_pipeline_status import DataPipelineQueueRow
from services.data_pipeline_status.constants import CANONICAL_QUEUE_CODES, QUEUE_LABELS


def build_pipeline_queues(db: Session) -> list[DataPipelineQueueRow]:
    builders = {
        "import": _import_queue,
        "enrichment": _enrichment_queue,
        "photo_review": _photo_queue,
        "verification": _verification_queue,
    }
    return [builders[code](db) for code in CANONICAL_QUEUE_CODES]


def _import_queue(db: Session) -> DataPipelineQueueRow:
    pending = _job_count(db, CityAdminImportJob.status == "queued")
    running = _job_count(db, CityAdminImportJob.status == "running")
    failed = _job_count(db, CityAdminImportJob.status.in_(("failed", "stalled")))
    return _row("import", pending, running, failed)


def _enrichment_queue(db: Session) -> DataPipelineQueueRow:
    pending = _task_count(db, EnrichmentTask.status == "queued")
    running = _task_count(db, EnrichmentTask.status == "running")
    failed = _task_count(db, EnrichmentTask.status == "failed")
    return _row("enrichment", pending, running, failed)


def _photo_queue(db: Session) -> DataPipelineQueueRow:
    pending = _image_count(db, PlaceImage.status == "needs_review")
    return _row("photo_review", pending, 0, 0)


def _verification_queue(db: Session) -> DataPipelineQueueRow:
    pending = _review_count(db, ReviewQueueItem.status == "open")
    return _row("verification", pending, 0, 0)


def _row(code: str, pending: int, running: int, failed: int) -> DataPipelineQueueRow:
    status = "idle"
    if failed > 0:
        status = "error"
    elif running > 0 or pending > 10:
        status = "warning"
    elif pending > 0 or running > 0:
        status = "ok"
    return DataPipelineQueueRow(
        code=code,
        label=QUEUE_LABELS[code],
        pending_count=pending,
        running_count=running,
        failed_count=failed,
        status=status,
        updated_at=datetime.utcnow(),
    )


def _job_count(db: Session, *filters) -> int:
    return int(db.query(func.count(CityAdminImportJob.id)).filter(*filters).scalar() or 0)


def _task_count(db: Session, *filters) -> int:
    return int(db.query(func.count(EnrichmentTask.id)).filter(*filters).scalar() or 0)


def _image_count(db: Session, *filters) -> int:
    return int(db.query(func.count(PlaceImage.id)).filter(*filters).scalar() or 0)


def _review_count(db: Session, *filters) -> int:
    return int(db.query(func.count(ReviewQueueItem.id)).filter(*filters).scalar() or 0)
