from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination
from models.destination_data_pipeline import DestinationDataPipelineRun
from schemas.destination_data_pipeline import DestinationPipelineRunRead


def serialize_run(run: DestinationDataPipelineRun, destination: Destination) -> DestinationPipelineRunRead:
    return DestinationPipelineRunRead(
        id=run.id,
        destination_id=run.destination_id,
        destination_slug=destination.slug,
        status=run.status,
        stage=run.stage,
        mode=run.mode,
        dry_run=run.dry_run,
        scope_ids=[int(value) for value in (run.scope_ids or [])],
        counters={key: int(value) for key, value in (run.counters or {}).items()},
        errors=list(run.errors or []),
        message=run.message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        heartbeat_at=run.heartbeat_at,
        created_at=run.created_at,
    )


def latest_run(db: Session, destination_id: int) -> DestinationDataPipelineRun | None:
    return (
        db.query(DestinationDataPipelineRun)
        .filter(DestinationDataPipelineRun.destination_id == destination_id)
        .order_by(DestinationDataPipelineRun.created_at.desc(), DestinationDataPipelineRun.id.desc())
        .first()
    )
