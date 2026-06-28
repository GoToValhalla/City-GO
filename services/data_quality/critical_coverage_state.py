"""Persist Critical Coverage v2 state into existing data_quality_issues.

This is a no-migration materialization layer. It stores the current per-place
quality bucket and city-level snapshot as deterministic DataQualityIssue rows so
operators can refresh and inspect persisted state before we introduce dedicated
indexed tables.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.data_quality import DataQualityIssue
from services.data_quality.critical_coverage import (
    build_city_critical_coverage,
    list_city_critical_coverage_places,
)
from services.data_quality.fingerprint import issue_fingerprint

ISSUE_CRITICAL_COVERAGE_STATE = "critical_coverage_state"
ISSUE_CRITICAL_COVERAGE_CITY_SNAPSHOT = "critical_coverage_city_snapshot"
SOURCE_CRITICAL_COVERAGE_V2 = "critical_coverage_v2"


def refresh_city_critical_coverage_state(
    db: Session,
    *,
    city_slug: str,
    category: str | None = None,
    limit: int | None = None,
) -> dict[str, Any] | None:
    payload = list_city_critical_coverage_places(
        db,
        city_slug=city_slug,
        category=category,
        limit=limit or 100_000,
        offset=0,
    )
    if payload is None:
        return None

    now = datetime.utcnow()
    counters: Counter[str] = Counter()
    active_fingerprints: set[str] = set()
    created = updated = unchanged = 0

    for item in payload["items"]:
        place = item["place"]
        bucket = _primary_bucket(item)
        counters[bucket] += 1
        fingerprint = issue_fingerprint(
            place_id=int(place["id"]),
            city_id=int(payload["city_id"]),
            issue_type=ISSUE_CRITICAL_COVERAGE_STATE,
            reason="state",
            source=SOURCE_CRITICAL_COVERAGE_V2,
        )
        active_fingerprints.add(fingerprint)
        stable_evidence = {
            "bucket": bucket,
            "profile_key": item["profile_key"],
            "is_tourist_eligible": item["is_tourist_eligible"],
            "route_status": item["route_status"],
            "card_status": item["card_status"],
            "route_blockers": item["route_blockers"],
            "card_blockers": item["card_blockers"],
            "auto_enrichment_candidates": item["auto_enrichment_candidates"],
            "manual_review_items": item["manual_review_items"],
            "optional_gaps": item["optional_gaps"],
            "confidence_flags": item["confidence_flags"],
            "place_snapshot": place,
        }
        evidence = {**stable_evidence, "generated_at": now.isoformat()}
        issue = db.query(DataQualityIssue).filter(DataQualityIssue.fingerprint == fingerprint).first()
        if issue is None:
            issue = DataQualityIssue(
                place_id=int(place["id"]),
                city_id=int(payload["city_id"]),
                issue_type=ISSUE_CRITICAL_COVERAGE_STATE,
                severity=_severity(bucket),
                status="current",
                reason="state",
                source=SOURCE_CRITICAL_COVERAGE_V2,
                evidence=evidence,
                fingerprint=fingerprint,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(issue)
            created += 1
            continue
        before = (
            issue.severity,
            issue.status,
            _stable_evidence(issue.evidence),
        )
        issue.severity = _severity(bucket)
        issue.status = "current"
        issue.reason = "state"
        issue.source = SOURCE_CRITICAL_COVERAGE_V2
        issue.evidence = evidence
        issue.last_seen_at = now
        issue.resolved_at = None
        if before == (issue.severity, issue.status, stable_evidence):
            unchanged += 1
        else:
            updated += 1

    resolved = 0
    if category is None:
        query = db.query(DataQualityIssue).filter(
            DataQualityIssue.city_id == int(payload["city_id"]),
            DataQualityIssue.issue_type == ISSUE_CRITICAL_COVERAGE_STATE,
            DataQualityIssue.source == SOURCE_CRITICAL_COVERAGE_V2,
        )
        if active_fingerprints:
            query = query.filter(~DataQualityIssue.fingerprint.in_(tuple(active_fingerprints)))
        for issue in query.all():
            if issue.status != "resolved":
                issue.status = "resolved"
                issue.resolved_at = now
                issue.last_seen_at = now
                resolved += 1

    snapshot_result = _upsert_city_snapshot(
        db,
        city_id=int(payload["city_id"]),
        city_slug=str(payload["city_slug"]),
        category=category,
        by_bucket=dict(counters),
        scanned=int(payload["total"]),
        generated_at=now,
    )

    db.commit()
    return {
        "city_id": payload["city_id"],
        "city_slug": payload["city_slug"],
        "city_name": payload["city_name"],
        "category": category,
        "scanned": payload["total"],
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "resolved": resolved,
        "by_bucket": dict(counters),
        "snapshot": snapshot_result,
        "generated_at": now.isoformat(),
        "issue_type": ISSUE_CRITICAL_COVERAGE_STATE,
        "snapshot_issue_type": ISSUE_CRITICAL_COVERAGE_CITY_SNAPSHOT,
        "source": SOURCE_CRITICAL_COVERAGE_V2,
    }


def _primary_bucket(item: dict[str, Any]) -> str:
    if not item.get("is_tourist_eligible"):
        return "not_applicable"
    if item.get("route_status") == "route_blocker":
        return "route_blocker"
    if item.get("card_status") == "card_blocker":
        return "card_blocker"
    if item.get("manual_review_items"):
        return "manual_review"
    if item.get("auto_enrichment_candidates"):
        return "auto_enrichment_candidate"
    if item.get("optional_gaps"):
        return "optional_gap"
    return "ready"


def _severity(bucket: str) -> str:
    if bucket == "route_blocker":
        return "critical"
    if bucket in {"card_blocker", "manual_review"}:
        return "warning"
    return "info"


def _snapshot_severity(by_bucket: dict[str, int]) -> str:
    if by_bucket.get("route_blocker", 0) > 0:
        return "critical"
    if by_bucket.get("card_blocker", 0) > 0 or by_bucket.get("manual_review", 0) > 0:
        return "warning"
    return "info"


def _stable_evidence(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    if evidence is None:
        return None
    return {key: value for key, value in evidence.items() if key != "generated_at"}


def _upsert_city_snapshot(
    db: Session,
    *,
    city_id: int,
    city_slug: str,
    category: str | None,
    by_bucket: dict[str, int],
    scanned: int,
    generated_at: datetime,
) -> dict[str, Any]:
    summary = build_city_critical_coverage(db, city_slug=city_slug, category=category) or {}
    reason = f"snapshot:{category}" if category else "snapshot"
    fingerprint = issue_fingerprint(
        place_id=None,
        city_id=city_id,
        issue_type=ISSUE_CRITICAL_COVERAGE_CITY_SNAPSHOT,
        reason=reason,
        source=SOURCE_CRITICAL_COVERAGE_V2,
    )
    stable_evidence = {
        "city_slug": city_slug,
        "category": category,
        "scanned": scanned,
        "by_bucket": by_bucket,
        "summary": summary,
    }
    evidence = {**stable_evidence, "generated_at": generated_at.isoformat()}
    severity = _snapshot_severity(by_bucket)
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.fingerprint == fingerprint).first()
    if issue is None:
        db.add(DataQualityIssue(
            place_id=None,
            city_id=city_id,
            issue_type=ISSUE_CRITICAL_COVERAGE_CITY_SNAPSHOT,
            severity=severity,
            status="current",
            reason=reason,
            source=SOURCE_CRITICAL_COVERAGE_V2,
            evidence=evidence,
            fingerprint=fingerprint,
            first_seen_at=generated_at,
            last_seen_at=generated_at,
        ))
        return {"created": 1, "updated": 0, "unchanged": 0}

    before = (issue.severity, issue.status, _stable_evidence(issue.evidence))
    issue.severity = severity
    issue.status = "current"
    issue.reason = reason
    issue.source = SOURCE_CRITICAL_COVERAGE_V2
    issue.evidence = evidence
    issue.last_seen_at = generated_at
    issue.resolved_at = None
    if before == (issue.severity, issue.status, stable_evidence):
        return {"created": 0, "updated": 0, "unchanged": 1}
    return {"created": 0, "updated": 1, "unchanged": 0}
