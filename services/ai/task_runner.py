"""Choice-first AI task runner for admin data-quality workflows."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from models.ai_candidate import AICandidate, AITaskRun
from models.review_queue_item import ReviewQueueItem
from models.place import Place
from services.ai.budget_guard import attach_reservation, commit_budget, estimate_cost, release_budget, reserve_budget
from services.ai.providers import provider_for_key
from services.ai.task_registry import get_provider_for_task, get_task_spec


class ExplainReviewReasonOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    reasons: list[str] = Field(default_factory=list, max_length=8)
    evidence: list[dict[str, str]] = Field(default_factory=list, max_length=8)
    risk_level: str = Field(pattern="^(low|medium|high)$")


def estimate_task(
    db: Session,
    *,
    task_type: str,
    provider_key: str,
    review_queue_item_id: int | None,
) -> dict[str, Any]:
    task = get_task_spec(task_type)
    provider = get_provider_for_task(task_type, provider_key)
    prompt = _build_prompt(db, task_type=task_type, review_queue_item_id=review_queue_item_id)
    estimate = estimate_cost(
        text=prompt,
        input_usd_per_1m=provider.input_usd_per_1m,
        output_usd_per_1m=provider.output_usd_per_1m,
        output_tokens=provider.max_output_tokens,
    )
    return {
        "task_type": task.key,
        "provider_key": provider.key,
        "model_name": provider.model_name,
        "schema_version": task.schema_version,
        "input_tokens_estimate": estimate.input_tokens,
        "output_tokens_limit": estimate.output_tokens,
        "estimated_cost_usd": estimate.estimated_cost_usd,
        "writes_public_fields": task.writes_public_fields,
    }


def run_task(
    db: Session,
    *,
    actor: str,
    task_type: str,
    provider_key: str,
    review_queue_item_id: int | None,
) -> AITaskRun:
    task = get_task_spec(task_type)
    provider = get_provider_for_task(task_type, provider_key)
    prompt = _build_prompt(db, task_type=task_type, review_queue_item_id=review_queue_item_id)
    estimate = estimate_cost(
        text=prompt,
        input_usd_per_1m=provider.input_usd_per_1m,
        output_usd_per_1m=provider.output_usd_per_1m,
        output_tokens=provider.max_output_tokens,
    )
    reservation = reserve_budget(db, actor=actor, estimated_cost_usd=estimate.estimated_cost_usd)
    review_item = _review_item(db, review_queue_item_id)
    task_run = AITaskRun(
        task_type=task.key,
        provider_key=provider.key,
        model_name=provider.model_name,
        mode=task.mode,
        status="running",
        schema_version=task.schema_version,
        actor=actor,
        city_id=review_item.city_id if review_item is not None else None,
        place_id=review_item.place_id if review_item is not None else None,
        review_queue_item_id=review_item.id if review_item is not None else None,
        budget_reservation_id=reservation.id,
        input_tokens_estimate=estimate.input_tokens,
        output_tokens_limit=estimate.output_tokens,
        estimated_cost_usd=estimate.estimated_cost_usd,
        prompt_snapshot={"task": task.key, "prompt": prompt},
        started_at=datetime.utcnow(),
    )
    db.add(task_run)
    db.flush()
    attach_reservation(db, reservation=reservation, task_run_id=task_run.id)
    try:
        result = provider_for_key(provider.key).run_json(
            prompt=prompt,
            schema_name=task.schema_version,
            max_output_tokens=provider.max_output_tokens,
        )
        payload = _validate_payload(task.key, result.payload)
    except ValidationError as exc:
        task_run.status = "failed"
        task_run.error_code = "failed_invalid_schema"
        task_run.error_message = str(exc)[:2000]
        task_run.finished_at = datetime.utcnow()
        release_budget(db, reservation=reservation)
        db.add(task_run)
        db.flush()
        return task_run
    except Exception as exc:
        task_run.status = "failed"
        task_run.error_code = "failed_provider_error"
        task_run.error_message = str(exc)[:2000]
        task_run.actual_cost_usd = commit_budget(db, reservation=reservation, actual_cost_usd=None, status="failed_unknown_spend")
        task_run.finished_at = datetime.utcnow()
        db.add(task_run)
        db.flush()
        return task_run

    candidate = AICandidate(
        task_run_id=task_run.id,
        city_id=task_run.city_id,
        place_id=task_run.place_id,
        review_queue_item_id=task_run.review_queue_item_id,
        candidate_type=task.key,
        status="pending",
        proposed_payload=payload.model_dump(),
        evidence_payload={"schema_version": task.schema_version, "source": "ai_task_run"},
        confidence_score=None,
        created_by=provider.key,
    )
    task_run.status = "completed"
    task_run.output_snapshot = result.raw_output | {"payload": payload.model_dump()}
    task_run.actual_cost_usd = commit_budget(db, reservation=reservation, actual_cost_usd=result.actual_cost_usd)
    task_run.finished_at = datetime.utcnow()
    db.add_all([task_run, candidate])
    db.flush()
    return task_run


def resolve_candidate(
    db: Session,
    *,
    candidate_id: int,
    actor: str,
    resolution: str,
    note: str | None = None,
) -> AICandidate | None:
    candidate = db.query(AICandidate).filter(AICandidate.id == candidate_id).first()
    if candidate is None:
        return None
    if candidate.status != "pending":
        raise ValueError("candidate_already_resolved")
    candidate.status = resolution
    candidate.resolved_by = actor
    candidate.resolved_at = datetime.utcnow()
    candidate.resolution_note = note
    db.add(candidate)
    db.flush()
    return candidate


def list_candidates(db: Session, *, status: str = "pending") -> list[AICandidate]:
    return db.query(AICandidate).filter(AICandidate.status == status).order_by(AICandidate.created_at.asc()).all()


def list_task_runs(db: Session, *, limit: int = 50) -> list[AITaskRun]:
    return db.query(AITaskRun).order_by(AITaskRun.created_at.desc()).limit(limit).all()


def _validate_payload(task_type: str, payload: dict[str, object]) -> BaseModel:
    if task_type == "explain_review_reason":
        return ExplainReviewReasonOutput.model_validate(payload)
    raise ValueError("unsupported_task")


def _build_prompt(db: Session, *, task_type: str, review_queue_item_id: int | None) -> str:
    if task_type != "explain_review_reason":
        raise ValueError("unsupported_task")
    review_item = _review_item(db, review_queue_item_id)
    if review_item is None:
        raise ValueError("review_queue_item_id_required")
    place = db.query(Place).filter(Place.id == review_item.place_id).first()
    if place is None:
        raise ValueError("place_not_found")
    data = {
        "review_queue_item": {
            "id": review_item.id,
            "field_name": review_item.field_name,
            "reason": review_item.reason,
            "severity": review_item.severity,
            "payload": review_item.payload or {},
        },
        "place": {
            "id": place.id,
            "title": place.title,
            "category": place.category,
            "address": place.address,
            "quality_score": place.quality_score,
            "publication_status": place.publication_status,
        },
    }
    safe_data = _sanitize_untrusted_text(json.dumps(data, ensure_ascii=False, default=str))
    return (
        "Task: explain to a Russian-speaking City GO admin why this review queue item needs attention. "
        "Do not propose applying changes. Do not write public fields. "
        "Return JSON: summary, reasons[], evidence[], risk_level(low|medium|high).\n"
        f"<untrusted_data>{safe_data}</untrusted_data>"
    )


def _review_item(db: Session, review_queue_item_id: int | None) -> ReviewQueueItem | None:
    if review_queue_item_id is None:
        return None
    return db.query(ReviewQueueItem).filter(ReviewQueueItem.id == review_queue_item_id).first()


def _sanitize_untrusted_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    max_chars = 16_000
    if len(value) > max_chars:
        return value[:max_chars] + " [TRUNCATED]"
    return value
