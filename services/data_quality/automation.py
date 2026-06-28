"""Guarded data-quality automation for safe reversible fixes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.data_quality import DataQualityCandidate, DataQualityIssue
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.data_quality.constants import ISSUE_ROUTE_SUSPICIOUS, STOPLIST_CATEGORIES
from services.data_quality.fingerprint import candidate_fingerprint

AUTOMATION_ACTION = "auto_exclude_stoplist_from_routes"
CANDIDATE_TYPE = "route_eligibility_auto_exclusion"
ROUTE_EXCLUSION_REASON = "non_tourist_category_policy"
MIN_ROUTE_ELIGIBLE_AFTER_AUTOMATION = 8


def preview_automation(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    selected = _select_route_exclusion_items(db, payload)
    return _automation_payload(selected, status="preview")


def apply_automation(db: Session, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    if payload.get("confirm") is not True:
        raise ValueError("confirm=true required")
    reason = str(payload.get("reason") or "").strip() or "safe route stoplist automation"
    selected = _select_route_exclusion_items(db, payload)
    now = datetime.utcnow()
    applied_candidates: list[int] = []
    for item in selected["applicable"]:
        issue: DataQualityIssue = item["issue"]
        place: Place = item["place"]
        old_value = {
            "is_route_eligible": bool(place.is_route_eligible),
            "route_exclusion_reason": place.route_exclusion_reason,
        }
        new_value = {
            "is_route_eligible": False,
            "route_exclusion_reason": ROUTE_EXCLUSION_REASON,
        }
        patch = {
            "action": AUTOMATION_ACTION,
            "field": "is_route_eligible",
            "old_value": old_value,
            "new_value": new_value,
            "rollback_patch": old_value,
            "rule_id": ROUTE_EXCLUSION_REASON,
            "reason": reason,
        }
        fingerprint = candidate_fingerprint(
            issue_id=issue.id,
            candidate_type=CANDIDATE_TYPE,
            patch={"action": AUTOMATION_ACTION, "new_value": False, "rule_id": ROUTE_EXCLUSION_REASON},
        )
        candidate = db.query(DataQualityCandidate).filter(DataQualityCandidate.fingerprint == fingerprint).first()
        if candidate is None:
            candidate = DataQualityCandidate(
                issue_id=issue.id,
                place_id=place.id,
                city_id=place.city_id,
                candidate_type=CANDIDATE_TYPE,
                proposed_patch=patch,
                evidence={
                    "issue_type": issue.issue_type,
                    "issue_evidence": issue.evidence or {},
                    "matched_categories": item["matched_categories"],
                    "automation_action": AUTOMATION_ACTION,
                    "confidence": item["confidence"],
                },
                source="deterministic_automation",
                confidence=item["confidence"],
                status="auto_applied",
                decided_at=now,
                decided_by=actor,
                fingerprint=fingerprint,
            )
            db.add(candidate)
            db.flush()
        else:
            candidate.status = "auto_applied"
            candidate.decided_at = now
            candidate.decided_by = actor
            candidate.proposed_patch = patch
            candidate.evidence = {**(candidate.evidence or {}), "reapplied_at": now.isoformat()}
        candidate.rollback_ref = f"data_quality_candidate:{candidate.id}"
        applied_candidates.append(candidate.id)

        place.is_route_eligible = False
        place.route_exclusion_reason = ROUTE_EXCLUSION_REASON
        issue.status = "auto_applied"
        issue.resolved_at = now
        issue.last_seen_at = now
        write_admin_audit_log(
            db,
            actor=actor,
            action="data_quality_automation_auto_exclude_stoplist_from_routes",
            entity_type="place",
            entity_id=place.id,
            old_value=old_value,
            new_value={**new_value, "issue_id": issue.id, "candidate_id": candidate.id},
            reason=reason,
        )
    db.commit()
    result = _automation_payload(selected, status="applied")
    result["candidate_ids"] = applied_candidates
    return result


def rollback_automation(db: Session, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    if payload.get("confirm") is not True:
        raise ValueError("confirm=true required")
    raw_ids = payload.get("candidate_ids") or []
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("candidate_ids required")
    candidate_ids = [int(item) for item in raw_ids]
    candidates = db.query(DataQualityCandidate).filter(
        DataQualityCandidate.id.in_(candidate_ids),
        DataQualityCandidate.candidate_type == CANDIDATE_TYPE,
        DataQualityCandidate.status == "auto_applied",
    ).all()
    now = datetime.utcnow()
    restored = 0
    restored_ids: list[int] = []
    for candidate in candidates:
        place = db.query(Place).filter(Place.id == candidate.place_id).first() if candidate.place_id else None
        if place is None:
            continue
        patch = candidate.proposed_patch or {}
        rollback_patch = patch.get("rollback_patch") if isinstance(patch.get("rollback_patch"), dict) else {}
        old_value = {
            "is_route_eligible": bool(place.is_route_eligible),
            "route_exclusion_reason": place.route_exclusion_reason,
        }
        place.is_route_eligible = bool(rollback_patch.get("is_route_eligible", True))
        place.route_exclusion_reason = rollback_patch.get("route_exclusion_reason")
        candidate.status = "rolled_back"
        candidate.decided_at = now
        candidate.decided_by = actor
        issue = db.query(DataQualityIssue).filter(DataQualityIssue.id == candidate.issue_id).first()
        if issue is not None:
            issue.status = "open"
            issue.resolved_at = None
            issue.last_seen_at = now
        write_admin_audit_log(
            db,
            actor=actor,
            action="data_quality_automation_rollback_auto_exclude_stoplist_from_routes",
            entity_type="place",
            entity_id=place.id,
            old_value=old_value,
            new_value={
                "is_route_eligible": place.is_route_eligible,
                "route_exclusion_reason": place.route_exclusion_reason,
                "candidate_id": candidate.id,
            },
            reason=str(payload.get("reason") or "rollback data quality automation"),
        )
        restored += 1
        restored_ids.append(candidate.id)
    db.commit()
    return {
        "action_type": "rollback_auto_exclude_stoplist_from_routes",
        "status": "rolled_back",
        "affected_count": restored,
        "candidate_ids": restored_ids,
        "warnings": [] if restored == len(candidate_ids) else ["Некоторые candidate_ids не найдены или уже не auto_applied."],
    }


def _select_route_exclusion_items(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    limit = int(payload.get("limit") or 500)
    query = db.query(DataQualityIssue, Place).join(Place, Place.id == DataQualityIssue.place_id).filter(
        DataQualityIssue.issue_type == ISSUE_ROUTE_SUSPICIOUS,
        DataQualityIssue.status == "open",
        Place.is_route_eligible.is_(True),
    )
    city_id = payload.get("city_id")
    city_slug = payload.get("city_slug")
    if city_id is not None:
        query = query.filter(DataQualityIssue.city_id == int(city_id))
    if city_slug:
        query = query.join(City, City.id == DataQualityIssue.city_id).filter(City.slug == str(city_slug))
    rows = query.order_by(DataQualityIssue.last_seen_at.desc(), DataQualityIssue.id.asc()).limit(limit).all()
    items = [_item(issue, place) for issue, place in rows]
    eligible_by_city = dict(
        db.query(Place.city_id, func.count(Place.id)).filter(Place.is_route_eligible.is_(True)).group_by(Place.city_id).all()
    )
    candidates_by_city: Counter[int] = Counter(item["place"].city_id for item in items if item["eligible"])
    applicable: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for item in items:
        place: Place = item["place"]
        if not item["eligible"]:
            blocked.append({**item, "blocked_reason": "not_confirmed_stoplist_category"})
            continue
        remaining = int(eligible_by_city.get(place.city_id, 0)) - int(candidates_by_city.get(place.city_id, 0))
        if remaining < MIN_ROUTE_ELIGIBLE_AFTER_AUTOMATION:
            blocked.append({**item, "blocked_reason": "route_inventory_guard"})
            continue
        applicable.append(item)
    return {"applicable": applicable, "blocked": blocked}


def _item(issue: DataQualityIssue, place: Place) -> dict[str, Any]:
    matched = _matched_categories(issue, place)
    return {
        "issue": issue,
        "place": place,
        "matched_categories": sorted(matched),
        "eligible": bool(matched),
        "confidence": 1.0 if matched else 0.0,
    }


def _matched_categories(issue: DataQualityIssue, place: Place) -> set[str]:
    evidence = issue.evidence or {}
    raw = evidence.get("matched_categories") or []
    values = set()
    if isinstance(raw, list):
        values.update(str(item).strip().lower() for item in raw if item)
    values.update(str(item).strip().lower() for item in (place.category, place.canonical_category) if item)
    return values & set(STOPLIST_CATEGORIES)


def _automation_payload(selected: dict[str, list[dict[str, Any]]], *, status: str) -> dict[str, Any]:
    applicable = selected["applicable"]
    blocked = selected["blocked"]
    return {
        "action_type": AUTOMATION_ACTION,
        "status": status,
        "affected_count": len(applicable),
        "blocked_count": len(blocked),
        "sample": [_sample(item) for item in applicable[:50]],
        "blocked_sample": [_sample(item, blocked_reason=item.get("blocked_reason")) for item in blocked[:50]],
        "grouped_by_city": dict(Counter(str(item["place"].city_id) for item in applicable)),
        "grouped_by_category": dict(Counter((item["place"].category or "unknown") for item in applicable)),
        "warnings": _warnings(blocked),
        "proposed_patch": {
            "is_route_eligible": False,
            "route_exclusion_reason": ROUTE_EXCLUSION_REASON,
            "reversible": True,
            "min_route_eligible_after_automation": MIN_ROUTE_ELIGIBLE_AFTER_AUTOMATION,
        },
    }


def _sample(item: dict[str, Any], *, blocked_reason: str | None = None) -> dict[str, Any]:
    issue: DataQualityIssue = item["issue"]
    place: Place = item["place"]
    payload = {
        "issue_id": issue.id,
        "place_id": place.id,
        "city_id": place.city_id,
        "title": place.title,
        "category": place.category,
        "matched_categories": item["matched_categories"],
        "confidence": item["confidence"],
    }
    if blocked_reason:
        payload["blocked_reason"] = blocked_reason
    return payload


def _warnings(blocked: list[dict[str, Any]]) -> list[str]:
    by_reason = Counter(str(item.get("blocked_reason") or "unknown") for item in blocked)
    warnings = []
    if by_reason.get("route_inventory_guard"):
        warnings.append(
            f"{by_reason['route_inventory_guard']} мест не тронуты: после автоисключения в городе осталось бы меньше route-eligible POI."
        )
    if by_reason.get("not_confirmed_stoplist_category"):
        warnings.append(f"{by_reason['not_confirmed_stoplist_category']} issues требуют ручной проверки категории.")
    return warnings
