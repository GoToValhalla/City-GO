"""Persist Critical Coverage v2 state into existing data_quality_issues.

This is a no-migration materialization layer. It stores the current per-place
quality bucket as a deterministic DataQualityIssue row so operators can refresh
and inspect persisted state before we introduce a dedicated indexed table.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.data_quality import DataQualityIssue
from services.data_quality.critical_coverage import list_city_critical_coverage_places
from services.data_quality.fingerprint import issue_fingerprint

ISSUE_CRITICAL_COVERAGE_STATE = "critical_coverage_state"
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
        "generated_at": now.isoformat(),
        "issue_type": ISSUE_CRITICAL_COVERAGE_STATE,
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


def _stable_evidence(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    if evidence is None:
        return None
    return {key: value for key, value in evidence.items() if key != "generated_at"}
