"""Метрики мониторинга Data Pipeline."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import EnrichmentTask
from models.place import Place
from models.place_image import PlaceImage
from models.place_merge_review import ReviewItem
from models.review_queue_item import ReviewQueueItem
from schemas.data_pipeline_status import DataPipelineMetrics


def build_pipeline_metrics(db: Session) -> DataPipelineMetrics:
    places_total = _count(db, Place)
    without_coords = _count(
        db,
        Place,
        or_(Place.lat.is_(None), Place.lng.is_(None)),
    )
    route_eligible = _count(db, Place, Place.is_route_eligible.is_(True))
    review_open = _count(db, ReviewQueueItem, ReviewQueueItem.status == "open")
    pending_photos = _count(db, PlaceImage, PlaceImage.status == "needs_review")
    active_imports = _count(
        db,
        CityAdminImportJob,
        CityAdminImportJob.status.in_(("queued", "running")),
    )
    active_enrichment = _count(
        db,
        EnrichmentTask,
        EnrichmentTask.status.in_(("queued", "running")),
    )
    merge_reviews = _count(db, ReviewItem, ReviewItem.status == "pending")
    return DataPipelineMetrics(
        places_total=places_total,
        places_without_coordinates=without_coords,
        places_route_eligible=route_eligible,
        open_review_items=review_open,
        pending_photos=pending_photos,
        active_import_jobs=active_imports,
        active_enrichment_tasks=active_enrichment,
        pending_merge_reviews=merge_reviews,
    )


def _count(db: Session, model, *filters) -> int:
    query = db.query(func.count(model.id))
    if filters:
        query = query.filter(*filters)
    return int(query.scalar() or 0)
