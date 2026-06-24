"""Лёгкий workflow registry поверх существующих фоновых операций."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from models.place import Place
from models.taxonomy import WorkflowOperation
from services.quality_score_v2 import calculate_quality_v2

WORKFLOW_REGISTRY: dict[str, tuple[str, ...]] = {
    "after_import": ("normalize_taxonomy", "validate_data", "detect_duplicates", "calculate_quality", "queue_enrichment", "queue_verification"),
    "after_place_confirmation": ("recalculate_confidence", "validate_publication", "enable_search"),
    "after_photo_confirmation": ("update_primary_photo", "calculate_quality", "resolve_no_photo"),
    "after_category_change": ("recalculate_route_eligibility", "calculate_quality", "invalidate_route_cache"),
}


def run_workflow(db: Session, *, workflow: str, request_id: str, idempotency_key: str, entity_type: str, entity_id: str | None, payload: dict[str, object], actor: str) -> WorkflowOperation:
    if workflow not in WORKFLOW_REGISTRY:
        raise ValueError("Неизвестный workflow")
    key = f"{workflow}:{idempotency_key}"
    existing = db.query(WorkflowOperation).filter(WorkflowOperation.idempotency_key == key).first()
    if existing:
        return existing
    operation = WorkflowOperation(
        id=uuid4().hex, workflow=workflow, request_id=request_id, idempotency_key=key,
        entity_type=entity_type, entity_id=entity_id, payload=payload, actor=actor,
        status="running", steps=[{"name": step, "status": "pending"} for step in WORKFLOW_REGISTRY[workflow]],
    )
    db.add(operation)
    db.flush()
    try:
        _execute(db, operation)
        operation.status = "completed"
        operation.finished_at = datetime.utcnow()
    except Exception as exc:
        operation.status = "failed"
        operation.error_message = str(exc)
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


def retry_workflow(db: Session, operation: WorkflowOperation) -> WorkflowOperation:
    if operation.status != "failed" or operation.retry_count >= operation.max_retries:
        return operation
    operation.retry_count += 1
    operation.status = "running"
    operation.error_message = None
    _execute(db, operation)
    operation.status = "completed"
    operation.finished_at = datetime.utcnow()
    db.commit()
    return operation


def _execute(db: Session, operation: WorkflowOperation) -> None:
    completed: list[dict[str, object]] = []
    for raw in operation.steps:
        step = dict(raw)
        operation.current_step = str(step["name"])
        _execute_step(db, operation, operation.current_step)
        step["status"] = "completed"
        step["finished_at"] = datetime.utcnow().isoformat()
        completed.append(step)
        operation.steps = completed + [item for item in operation.steps[len(completed):]]
        db.add(operation)
        db.flush()


def _execute_step(db: Session, operation: WorkflowOperation, step: str) -> None:
    if operation.entity_type != "place" or not operation.entity_id:
        return
    place = db.query(Place).filter(Place.id == int(operation.entity_id)).first()
    if place is None:
        raise ValueError("Место не найдено")
    if step == "calculate_quality":
        quality = calculate_quality_v2(place)
        place.quality_score = quality.score
        place.quality_tier = quality.bucket
    elif step == "enable_search":
        place.is_searchable = place.verification_status == "verified" and place.category_id is not None
    elif step == "recalculate_route_eligibility":
        place.is_route_eligible = bool(place.category_ref and place.category_ref.is_route_eligible)
    db.add(place)
