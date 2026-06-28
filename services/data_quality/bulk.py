"""Safe bulk previews and applications for data quality issues."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha256

from sqlalchemy.orm import Session

from models.data_quality import DataQualityCandidate, DataQualityIssue
from models.place_field_confidence import PlaceFieldConfidence
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.admin_audit_service import write_admin_audit_log
from services.data_quality.constants import BULK_ACTIONS, ISSUE_POSSIBLE_DUPLICATE
from services.data_quality.detect import detect_place_issues
from services.data_quality.fingerprint import candidate_fingerprint
from services.data_quality.query import _issue_payload, _issue_query


def preview_bulk_action(db: Session, payload: dict[str, object]) -> dict[str, object]:
    action = _action(payload)
    issues = _selected_issues(db, payload)
    sample = issues[: min(len(issues), 50)]
    return {
        "preview_token": _preview_key(action, payload),
        "action_type": action,
        "affected_count": len(issues),
        "sample": [_issue_payload(db, issue) for issue in sample],
        "grouped_by_city": _group(db, issues, "city"),
        "grouped_by_category": _group(db, issues, "category"),
        "grouped_by_reason": dict(Counter(issue.reason or "unknown" for issue in issues)),
        "warnings": _warnings(action),
        "proposed_patch": _patch_summary(action, payload),
    }


def apply_bulk_action(db: Session, payload: dict[str, object], *, actor: str) -> dict[str, object]:
    action = _action(payload)
    if payload.get("confirm") is not True:
        raise ValueError("confirm=true required")
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise ValueError("reason required")
    issues = _selected_issues(db, payload)
    created = _apply_action(db, issues, action=action, actor=actor, reason=reason, payload=payload)
    write_admin_audit_log(
        db, actor=actor, action=f"data_quality_bulk_{action}", entity_type="data_quality_issue",
        entity_id=None, old_value=None, new_value={"affected": len(issues), "created_candidates": created}, reason=reason,
    )
    db.commit()
    return {"action_type": action, "affected_count": len(issues), "created_candidates": created, "status": "done"}


def _action(payload: dict[str, object]) -> str:
    action = str(payload.get("action_type") or "")
    if action not in BULK_ACTIONS:
        raise ValueError("unsupported action_type")
    return action


def _selected_issues(db: Session, payload: dict[str, object]) -> list[DataQualityIssue]:
    ids = payload.get("issue_ids") or []
    limit = int(payload.get("limit") or 500)
    if ids:
        return db.query(DataQualityIssue).filter(DataQualityIssue.id.in_(ids)).limit(limit).all()
    filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
    return _issue_query(db, filters).limit(limit).all()


def _apply_action(
    db: Session,
    issues: list[DataQualityIssue],
    *,
    action: str,
    actor: str,
    reason: str,
    payload: dict[str, object],
) -> int:
    if action == "propose_exclude_from_routes":
        return _create_route_candidates(db, issues, actor=actor, reason=reason)
    if action == "propose_duplicate_review":
        return _create_duplicate_review_candidates(db, issues, actor=actor, reason=reason)
    if action in {"defer_issues", "ignore_issues"}:
        return _set_status(issues, "deferred" if action == "defer_issues" else "ignored")
    if action == "mark_resolved_if_current_state_ok":
        return _mark_resolved(db, issues, payload)
    return 0


def _create_route_candidates(db: Session, issues: list[DataQualityIssue], *, actor: str, reason: str) -> int:
    created = 0
    patch = {"is_route_eligible": False, "reason": reason}
    for issue in issues:
        fingerprint = candidate_fingerprint(issue_id=issue.id, candidate_type="route_eligibility_change", patch=patch)
        existing = db.query(DataQualityCandidate).filter(DataQualityCandidate.fingerprint == fingerprint).first()
        if existing is None:
            db.add(DataQualityCandidate(
                issue_id=issue.id, place_id=issue.place_id, city_id=issue.city_id,
                candidate_type="route_eligibility_change", proposed_patch=patch,
                evidence={"issue_type": issue.issue_type, "actor": actor}, source="deterministic",
                confidence=1.0, status="pending", fingerprint=fingerprint,
            ))
            created += 1
        issue.status = "candidate_created"
    return created


def _create_duplicate_review_candidates(db: Session, issues: list[DataQualityIssue], *, actor: str, reason: str) -> int:
    created = 0
    for issue in issues:
        if issue.issue_type != ISSUE_POSSIBLE_DUPLICATE:
            continue
        evidence = issue.evidence or {}
        duplicate_place_ids = _duplicate_place_ids(issue)
        patch = {
            "action": "manual_duplicate_review",
            "duplicate_place_ids": duplicate_place_ids,
            "reason": reason,
        }
        fingerprint = candidate_fingerprint(issue_id=issue.id, candidate_type="duplicate_review", patch=patch)
        existing = db.query(DataQualityCandidate).filter(DataQualityCandidate.fingerprint == fingerprint).first()
        if existing is None:
            db.add(DataQualityCandidate(
                issue_id=issue.id,
                place_id=issue.place_id,
                city_id=issue.city_id,
                candidate_type="duplicate_review",
                proposed_patch=patch,
                evidence={
                    "issue_type": issue.issue_type,
                    "actor": actor,
                    "title": evidence.get("title"),
                    "normalized_title": evidence.get("normalized_title"),
                    "duplicate_place_ids": duplicate_place_ids,
                },
                source="deterministic",
                confidence=0.85,
                status="pending",
                fingerprint=fingerprint,
            ))
            created += 1
        issue.status = "candidate_created"
    return created


def _duplicate_place_ids(issue: DataQualityIssue) -> list[int]:
    raw_ids = (issue.evidence or {}).get("duplicate_place_ids") or []
    ids: set[int] = set()
    if isinstance(raw_ids, list):
        for raw_id in raw_ids:
            try:
                ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
    if issue.place_id is not None:
        ids.add(issue.place_id)
    return sorted(ids)


def _set_status(issues: list[DataQualityIssue], status: str) -> int:
    for issue in issues:
        issue.status = status
    return 0


def _mark_resolved(db: Session, issues: list[DataQualityIssue], payload: dict[str, object]) -> int:
    now = datetime.utcnow()
    resolved = 0
    for issue in issues:
        if not _still_applies(db, issue):
            issue.status = "resolved"
            issue.resolved_at = now
            issue.evidence = {**(issue.evidence or {}), "resolution_payload": payload}
            resolved += 1
    return resolved


def _still_applies(db: Session, issue: DataQualityIssue) -> bool:
    place = db.query(Place).filter(Place.id == issue.place_id).first() if issue.place_id else None
    if place is None:
        return False
    drafts = detect_place_issues(
        place,
        source_observations=db.query(SourceObservation).filter(SourceObservation.canonical_place_id == place.id).all(),
        confidence_fields=db.query(PlaceFieldConfidence).filter(PlaceFieldConfidence.place_id == place.id).all(),
        review_items=db.query(ReviewQueueItem).filter(ReviewQueueItem.place_id == place.id).all(),
    )
    return any(draft.fingerprint == issue.fingerprint for draft in drafts)


def _group(db: Session, issues: list[DataQualityIssue], kind: str) -> dict[str, int]:
    values = [_group_value(db, issue, kind) for issue in issues]
    return dict(Counter(value for value in values if value))


def _group_value(db: Session, issue: DataQualityIssue, kind: str) -> str | None:
    place = db.query(Place).filter(Place.id == issue.place_id).first() if issue.place_id else None
    if kind == "category":
        return place.category if place else None
    return str(issue.city_id) if issue.city_id is not None else None


def _warnings(action: str) -> list[str]:
    if action == "propose_exclude_from_routes":
        return ["Будут созданы предложения, места не изменятся."]
    if action == "propose_duplicate_review":
        return ["Будут созданы предложения ручной проверки дублей, места не изменятся."]
    return []


def _patch_summary(action: str, payload: dict[str, object]) -> dict[str, object]:
    if action == "propose_exclude_from_routes":
        return {"is_route_eligible": False, "reason": payload.get("reason")}
    if action == "propose_duplicate_review":
        return {"action": "manual_duplicate_review", "reason": payload.get("reason")}
    return {}


def _preview_key(action: str, payload: dict[str, object]) -> str:
    raw = str(payload.get("filters") or payload.get("issue_ids") or "all")
    return f"{action}:{sha256(raw.encode('utf-8')).hexdigest()[:16]}"