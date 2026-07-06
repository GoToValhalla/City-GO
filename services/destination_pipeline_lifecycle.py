from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.destination_data_pipeline import DestinationDataPipelineRun
from models.place import Place
from schemas.destination_data_pipeline import DestinationPipelineRunRequest
from services.destination_pipeline_counters import empty_counters


def create_run(db: Session, destination: Destination, body: DestinationPipelineRunRequest, scopes: list[DestinationScope], actor: str) -> DestinationDataPipelineRun:
    now = datetime.now(timezone.utc)
    run = DestinationDataPipelineRun(
        destination_id=destination.id, triggered_by=actor, status="running", stage="preparing",
        scope_ids=[scope.id for scope in scopes], counters=empty_counters() | {"scopes_total": len(scopes)},
        errors=[], idempotency_key=body.idempotency_key, dry_run=body.dry_run, mode=body.mode,
        started_at=now, heartbeat_at=now, message="Прогон запущен",
    )
    db.add(run)
    return run


def selected_scopes(db: Session, destination_id: int, scope_ids: list[int] | None) -> list[DestinationScope]:
    query = db.query(DestinationScope).filter(DestinationScope.destination_id == destination_id, DestinationScope.enabled.is_(True))
    if scope_ids:
        query = query.filter(DestinationScope.id.in_(scope_ids))
    return query.order_by(DestinationScope.priority.desc(), DestinationScope.id.asc()).all()


def idempotent_run(db: Session, destination_id: int, key: str | None) -> DestinationDataPipelineRun | None:
    return None if not key else db.query(DestinationDataPipelineRun).filter_by(destination_id=destination_id, idempotency_key=key).first()


def stage(run: DestinationDataPipelineRun, value: str) -> None:
    run.stage = value
    run.heartbeat_at = datetime.now(timezone.utc)


def member_places(db: Session, destination_id: int) -> list[Place]:
    return db.query(Place).join(DestinationPlaceMembership, DestinationPlaceMembership.place_id == Place.id).filter(DestinationPlaceMembership.destination_id == destination_id, DestinationPlaceMembership.is_hidden.is_(False), DestinationPlaceMembership.invalidated_at.is_(None)).all()
