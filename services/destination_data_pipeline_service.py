from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from models.destination_data_pipeline import DestinationDataPipelineRun
from models.place import Place
from schemas.destination_data_pipeline import DestinationPipelineRunRequest
from services.admin_audit_service import write_admin_audit_log
from services.destination_enrichment_pipeline import enrich_destination_places
from services.destination_import_service import import_destination_scope
from services.destination_pipeline_lifecycle import create_run, idempotent_run, member_places, selected_scopes, stage
from services.destination_pipeline_counters import add_counter, empty_counters
from services.destination_pipeline_recalc import recalculate_destination_memberships
from services.destination_readiness_service import build_destination_readiness

IMPORT_MODES = {"full", "import_only"}
ENRICH_MODES = {"full", "enrich_only"}
RECALC_MODES = {"full", "membership_recalc_only"}


def start_destination_pipeline(db: Session, destination: Destination, body: DestinationPipelineRunRequest, *, actor: str) -> DestinationDataPipelineRun:
    existing = idempotent_run(db, destination.id, body.idempotency_key)
    if existing is not None:
        return existing
    scopes = selected_scopes(db, destination.id, body.scope_ids)
    run = create_run(db, destination, body, scopes, actor)
    write_admin_audit_log(db, actor=actor, action="destination_pipeline_run_started", entity_type="destination", entity_id=destination.id, new_value={"mode": body.mode, "dry_run": body.dry_run, "scope_ids": run.scope_ids})
    db.commit()
    return _execute_run(db, destination, run, scopes, actor=actor)


def stop_destination_pipeline(db: Session, run: DestinationDataPipelineRun, *, actor: str) -> DestinationDataPipelineRun:
    if run.status not in {"queued", "running"}:
        raise ValueError("Завершённый прогон нельзя остановить")
    run.status = "cancelled"
    run.stage = "completed"
    run.finished_at = datetime.now(timezone.utc)
    run.message = "Прогон остановлен оператором"
    write_admin_audit_log(db, actor=actor, action="destination_pipeline_run_cancelled", entity_type="destination_pipeline_run", entity_id=run.id)
    db.commit()
    db.refresh(run)
    return run


def _execute_run(db: Session, destination: Destination, run: DestinationDataPipelineRun, scopes: list[DestinationScope], *, actor: str) -> DestinationDataPipelineRun:
    counters = empty_counters() | dict(run.counters or {})
    errors: list[dict[str, object]] = []
    places: list[Place] = []
    stage(run, "importing" if run.mode in IMPORT_MODES else "preparing")
    try:
        places = _import(db, destination, scopes, counters, run.dry_run) if run.mode in IMPORT_MODES else member_places(db, destination.id)
        stage(run, "enriching")
        if run.mode in ENRICH_MODES:
            enrich_destination_places(db, places, counters, actor=actor, dry_run=run.dry_run)
        stage(run, "recalculating_memberships")
        if run.mode in RECALC_MODES and not run.dry_run:
            recalculate_destination_memberships(db, destination, counters, run.scope_ids)
        stage(run, "completed")
        build_destination_readiness(db, destination)
        run.status = "partial_failed" if counters["errors_count"] else "succeeded"
        run.message = "Прогон завершён" if run.status == "succeeded" else "Прогон завершён с предупреждениями"
    except Exception as exc:
        add_counter(counters, "errors_count")
        errors.append({"stage": run.stage, "message": str(exc)[:500]})
        run.status, run.message = "failed", "Прогон завершился ошибкой"
    run.counters, run.errors = counters, errors
    run.finished_at = run.heartbeat_at = datetime.now(timezone.utc)
    write_admin_audit_log(db, actor=actor, action="destination_pipeline_run_finished", entity_type="destination_pipeline_run", entity_id=run.id, new_value={"status": run.status, "counters": counters})
    db.commit()
    db.refresh(run)
    return run


def _import(db: Session, destination: Destination, scopes: list[DestinationScope], counters: dict[str, int], dry_run: bool) -> list[Place]:
    counters["scopes_total"] = len(scopes)
    nested = [import_destination_scope(db, destination, scope, counters, dry_run=dry_run) for scope in scopes]
    return [place for group in nested for place in group]
