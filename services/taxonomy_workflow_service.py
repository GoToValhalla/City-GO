"""Лёгкий workflow registry поверх существующих фоновых операций."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from models.place import Place
from models.taxonomy import QualityIssue, QualityRule, WorkflowOperation
from services.place_publication_reconciliation import reconcile_published_place
from services.quality_score_v2 import calculate_quality_v2
from services.taxonomy_automation_service import normalize_place, validate_place

WORKFLOW_REGISTRY = {
    "after_import": (
        "normalize_taxonomy",
        "validate_data",
        "detect_duplicates",
        "calculate_quality",
        "queue_enrichment",
        "queue_verification",
    ),
    "after_place_confirmation": ("recalculate_confidence", "validate_publication", "enable_search"),
    "after_photo_confirmation": ("update_primary_photo", "calculate_quality", "resolve_no_photo"),
    "after_category_change": ("recalculate_route_eligibility", "calculate_quality", "invalidate_route_cache"),
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
    key = f"{workflow}:{idempotency_key}"
    existing = db.query(WorkflowOperation).filter(WorkflowOperation.idempotency_key == key).first()
    if existing:
        return existing
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
        steps=[{"name": step, "status": "pending"} for step in WORKFLOW_REGISTRY[workflow]],
    )
    db.add(operation)
    db.flush()
    try:
        _execute(db, operation)
        operation.status = "completed"
        operation.finished_at = datetime.utcnow()
    except Exception as exc:  # workflow outcome is persisted; caller decides rollback policy
        operation.status = "failed"
        operation.error_message = str(exc)
    db.add(operation)
    if commit:
        db.commit()
        db.refresh(operation)
    else:
        db.flush()
    return operation


def retry_workflow(db: Session, operation: WorkflowOperation) -> WorkflowOperation:
    if operation.status != "failed" or operation.retry_count >= operation.max_retries:
        return operation
    operation.retry_count += 1
    operation.status = "running"
    operation.error_message = None
    try:
        _execute(db, operation)
        operation.status = "completed"
        operation.finished_at = datetime.utcnow()
    except Exception as exc:
        operation.status = "failed"
        operation.error_message = str(exc)
    db.commit()
    return operation


def _execute(db: Session, operation: WorkflowOperation) -> None:
    completed: list[dict[str, object]] = []
    for raw in operation.steps:
        step = dict(raw)
        if step.get("status") == "completed":
            completed.append(step)
            continue
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
    if step == "normalize_taxonomy":
        normalize_place(db, place, actor=operation.actor)
    elif step in {"validate_data", "validate_publication"}:
        validate_place(db, place)
    elif step == "calculate_quality":
        quality = calculate_quality_v2(place)
        place.quality_score = quality.score
        place.quality_tier = quality.bucket
    elif step in {"enable_search", "recalculate_route_eligibility"}:
        reconcile_published_place(
            db,
            place,
            actor=operation.actor,
            source=f"taxonomy_workflow_{step}",
            reason=f"Taxonomy workflow: {step}",
            lock_place=False,
        )
    elif step == "resolve_no_photo":
        _resolve_issue(db, place.id, "photo_required")
    db.add(place)


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
