from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination
from models.destination_data_pipeline import DestinationDataPipelineRun
from models.place import Place
from models.place_merge_review import ReviewItem
from schemas.admin_review import ReviewItemRead
from schemas.destination_data_pipeline import (
    DestinationPipelineRunList, DestinationPipelineRunRequest,
    DestinationPipelineRunResponse, DestinationReadinessRead,
)
from services.admin_audit_service import write_admin_audit_log
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_data_pipeline_service import start_destination_pipeline, stop_destination_pipeline
from services.destination_pipeline_recalc import recalculate_destination_memberships
from services.destination_pipeline_runs import latest_run, serialize_run
from services.destination_readiness_service import build_destination_readiness


def start(db: Session, slug: str, body: DestinationPipelineRunRequest, *, actor: str) -> DestinationPipelineRunResponse:
    destination = _destination(db, slug)
    run = start_destination_pipeline(db, destination, body, actor=actor)
    return _response(run, destination, "Прогон обработан")


def latest(db: Session, slug: str) -> DestinationPipelineRunResponse | None:
    destination = _destination(db, slug)
    run = latest_run(db, destination.id)
    return None if run is None else _response(run, destination, "Последний прогон")


def list_runs(db: Session, slug: str, *, limit: int, offset: int) -> DestinationPipelineRunList:
    destination = _destination(db, slug)
    query = db.query(DestinationDataPipelineRun).filter_by(destination_id=destination.id)
    rows = query.order_by(DestinationDataPipelineRun.created_at.desc()).offset(offset).limit(limit).all()
    return DestinationPipelineRunList(
        items=[serialize_run(row, destination) for row in rows], total=query.count(),
        limit=limit, offset=offset,
    )


def read_run(db: Session, slug: str, run_id: int) -> DestinationPipelineRunResponse:
    destination = _destination(db, slug)
    return _response(_run(db, destination.id, run_id), destination, "Детали прогона")


def stop(db: Session, slug: str, run_id: int, *, actor: str) -> DestinationPipelineRunResponse:
    destination = _destination(db, slug)
    run = stop_destination_pipeline(db, _run(db, destination.id, run_id), actor=actor)
    return _response(run, destination, "Прогон остановлен")


def recalculate(db: Session, slug: str, scope_id: int | None, *, actor: str) -> dict[str, object]:
    destination = _destination(db, slug)
    counters = {"memberships_created": 0, "memberships_updated": 0, "errors_count": 0}
    result = recalculate_destination_memberships(
        db, destination, counters, [scope_id] if scope_id else None,
    )
    combined = result | counters
    write_admin_audit_log(db, actor=actor, action="destination_memberships_recalculated",
        entity_type="destination", entity_id=destination.id, new_value=combined)
    db.commit()
    return {"status": "ok", "message": "Принадлежность мест пересчитана", "result": combined}


def readiness(db: Session, slug: str) -> DestinationReadinessRead:
    result = build_destination_readiness(db, _destination(db, slug))
    db.commit()
    return result


def review_items(db: Session, slug: str) -> list[ReviewItemRead]:
    destination = _destination(db, slug)
    rows = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(
        ReviewItem.status == "pending", Place.destination_memberships.any(destination_id=destination.id),
    ).order_by(ReviewItem.created_at.desc()).limit(100).all()
    return [ReviewItemRead(id=item.id, place_id=item.place_id, place_name=title, source=item.source,
        confidence=item.confidence, status=item.status, reason=item.reason, created_at=item.created_at,
        place_version_at_creation=item.place_version_at_creation) for item, title in rows]


def _destination(db: Session, slug: str) -> Destination:
    destination = get_destination_by_slug(db, slug)
    if destination is None:
        raise LookupError("Направление не найдено")
    return destination


def _run(db: Session, destination_id: int, run_id: int) -> DestinationDataPipelineRun:
    run = db.query(DestinationDataPipelineRun).filter_by(destination_id=destination_id, id=run_id).first()
    if run is None:
        raise LookupError("Прогон не найден")
    return run


def _response(run, destination: Destination, fallback: str) -> DestinationPipelineRunResponse:
    return DestinationPipelineRunResponse(run=serialize_run(run, destination), message=run.message or fallback)
