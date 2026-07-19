"""Transactional taxonomy workflow engine with an explicit, executable DAG."""

from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.place import Place
from models.taxonomy import QualityIssue, QualityRule, WorkflowOperation
from services.place_publication_reconciliation import reconcile_published_place
from services.quality_score_v2 import calculate_quality_v2
from services.taxonomy_automation_service import normalize_place, validate_place

WORKFLOW_REGISTRY: dict[str, tuple[str, ...]] = {
    "after_import": ("normalize_taxonomy", "validate_data", "calculate_quality"),
    "after_place_confirmation": ("validate_publication", "reconcile_publication_route"),
    "after_photo_confirmation": ("calculate_quality", "resolve_no_photo", "reconcile_publication_route"),
    "after_category_change": ("calculate_quality", "reconcile_publication_route"),
    "after_place_update": ("calculate_quality", "reconcile_publication_route"),
}


def run_workflow(
    db: Session,
    *,
    workflow: str,
    request_id: str,
    idempotency_key: str,
    entity_type: str,
    entity_id: str | None,
    payload: dict[str, object],
    actor: str,
    commit: bool = True,
) -> WorkflowOperation:
    if workflow not in WORKFLOW_REGISTRY:
        raise ValueError("Неизвестный workflow")
    _validate_registry()
    _lock_entity(db, entity_type=entity_type, entity_id=entity_id)
    key = f"{workflow}:{idempotency_key}"

    existing = (
        db.query(WorkflowOperation)
        .filter(WorkflowOperation.idempotency_key == key)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if existing is not None:
        return existing

    pending_steps = [{"name": step, "status": "pending"} for step in WORKFLOW_REGISTRY[workflow]]
    operation = WorkflowOperation(
        id=uuid4().hex,
        workflow=workflow,
        request_id=request_id,
        idempotency_key=key,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        actor=actor,
        status="running",
        steps=pending_steps,
    )

    try:
        with db.begin_nested():
            db.add(operation)
            db.flush()
    except IntegrityError:
        existing = (
            db.query(WorkflowOperation)
            .filter(WorkflowOperation.idempotency_key == key)
            .populate_existing()
            .with_for_update()
            .one()
        )
        return existing

    try:
        with db.begin_nested():
            _execute(db, operation)
        operation.status = "completed"
        operation.finished_at = datetime.utcnow()
    except Exception as exc:
        operation.status = "failed"
        operation.error_message = str(exc)
        operation.current_step = None
        operation.steps = pending_steps
        operation.finished_at = datetime.utcnow()
    db.add(operation)

    if commit:
        db.commit()
        db.refresh(operation)
    else:
        db.flush()
    return operation


def retry_workflow(db: Session, operation: WorkflowOperation) -> WorkflowOperation:
    # Global workflow lock order is Place -> WorkflowOperation. The entity identity
    # is immutable workflow metadata, so it is safe to use it before refreshing the
    # operation row; every path then acquires locks in the same order.
    _lock_entity(db, entity_type=operation.entity_type, entity_id=operation.entity_id)
    locked = (
        db.query(WorkflowOperation)
        .filter(WorkflowOperation.id == operation.id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    if locked.status != "failed" or locked.retry_count >= locked.max_retries:
        return locked
    if locked.workflow not in WORKFLOW_REGISTRY:
        raise ValueError("Неизвестный workflow")
    _validate_registry()

    pending_steps = [{"name": step, "status": "pending"} for step in WORKFLOW_REGISTRY[locked.workflow]]
    locked.retry_count += 1
    locked.status = "running"
    locked.error_message = None
    locked.current_step = None
    locked.steps = pending_steps
    try:
        with db.begin_nested():
            _execute(db, locked)
        locked.status = "completed"
        locked.finished_at = datetime.utcnow()
    except Exception as exc:
        locked.status = "failed"
        locked.error_message = str(exc)
        locked.current_step = None
        locked.steps = pending_steps
        locked.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(locked)
    return locked


def _lock_entity(db: Session, *, entity_type: str, entity_id: str | None) -> None:
    if entity_type != "place" or not entity_id:
        return
    (
        db.query(Place)
        .filter(Place.id == int(entity_id))
        .populate_existing()
        .with_for_update()
        .one()
    )


def _execute(db: Session, operation: WorkflowOperation) -> None:
    completed: list[dict[str, object]] = []
    for raw in operation.steps:
        step = dict(raw)
        if step.get("status") == "completed":
            completed.append(step)
            continue
        step_name = str(step["name"])
        handler = STEP_HANDLERS.get(step_name)
        if handler is None:
            raise RuntimeError(f"Workflow step has no handler: {step_name}")
        operation.current_step = step_name
        handler(db, operation)
        step["status"] = "completed"
        step["finished_at"] = datetime.utcnow().isoformat()
        completed.append(step)
        operation.steps = completed + [item for item in operation.steps[len(completed):]]
        db.add(operation)
        db.flush()


def _place(db: Session, operation: WorkflowOperation) -> Place:
    if operation.entity_type != "place" or not operation.entity_id:
        raise ValueError("Workflow requires a place entity")
    place = db.query(Place).filter(Place.id == int(operation.entity_id)).first()
    if place is None:
        raise ValueError("Место не найдено")
    return place


def _normalize_taxonomy(db: Session, operation: WorkflowOperation) -> None:
    normalize_place(db, _place(db, operation), actor=operation.actor)


def _validate(db: Session, operation: WorkflowOperation) -> None:
    validate_place(db, _place(db, operation))


def _calculate_quality(db: Session, operation: WorkflowOperation) -> None:
    place = _place(db, operation)
    quality = calculate_quality_v2(place)
    place.quality_score = quality.score
    place.quality_tier = quality.bucket
    db.add(place)


def _reconcile(db: Session, operation: WorkflowOperation) -> None:
    place = _place(db, operation)
    reconcile_published_place(
        db,
        place,
        actor=operation.actor,
        source="taxonomy_workflow_reconcile_publication_route",
        reason="Taxonomy workflow reconciliation",
        lock_place=False,
    )


def _resolve_no_photo(db: Session, operation: WorkflowOperation) -> None:
    _resolve_issue(db, _place(db, operation).id, "photo_required")


STEP_HANDLERS: dict[str, Callable[[Session, WorkflowOperation], None]] = {
    "normalize_taxonomy": _normalize_taxonomy,
    "validate_data": _validate,
    "validate_publication": _validate,
    "calculate_quality": _calculate_quality,
    "reconcile_publication_route": _reconcile,
    "resolve_no_photo": _resolve_no_photo,
}


def _validate_registry() -> None:
    registered = {step for steps in WORKFLOW_REGISTRY.values() for step in steps}
    missing = sorted(registered - set(STEP_HANDLERS))
    unused = sorted(set(STEP_HANDLERS) - registered)
    if missing or unused:
        raise RuntimeError(f"Workflow registry mismatch: missing={missing}, unused={unused}")


def _resolve_issue(db: Session, place_id: int, rule_code: str) -> None:
    issues = (
        db.query(QualityIssue)
        .join(QualityRule, QualityIssue.rule_id == QualityRule.id)
        .filter(
            QualityIssue.place_id == place_id,
            QualityIssue.status == "open",
            QualityRule.code == rule_code,
        )
        .all()
    )
    for issue in issues:
        issue.status = "fixed"
        issue.fixed_at = datetime.utcnow()
        db.add(issue)


_validate_registry()
