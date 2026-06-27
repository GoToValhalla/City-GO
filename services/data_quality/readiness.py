"""Diagnostic data quality gates, non-blocking by default."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.config import settings
from services.data_quality.constants import (
    ISSUE_LOW_CONFIDENCE,
    ISSUE_MISSING_ADDRESS,
    ISSUE_MISSING_PHOTO,
    ISSUE_REQUIRES_REVIEW,
    ISSUE_ROUTE_SUSPICIOUS,
    OPEN_STATUSES,
)
from models.data_quality import DataQualityIssue

THRESHOLDS = {
    "photo_coverage": 0,
    "address_coverage": 0,
    "low_confidence": 50,
    "review_backlog": 50,
    "route_eligibility_suspicious": 0,
}


def diagnostic_gates(db: Session, *, city_id: int, city_slug: str) -> dict[str, object]:
    counts = _counts(db, city_id)
    gates = {
        "photo_coverage": _gate(counts.get(ISSUE_MISSING_PHOTO, 0), THRESHOLDS["photo_coverage"], city_slug, ISSUE_MISSING_PHOTO),
        "address_coverage": _gate(counts.get(ISSUE_MISSING_ADDRESS, 0), THRESHOLDS["address_coverage"], city_slug, ISSUE_MISSING_ADDRESS),
        "low_confidence": _gate(counts.get(ISSUE_LOW_CONFIDENCE, 0), THRESHOLDS["low_confidence"], city_slug, ISSUE_LOW_CONFIDENCE),
        "review_backlog": _gate(counts.get(ISSUE_REQUIRES_REVIEW, 0), THRESHOLDS["review_backlog"], city_slug, ISSUE_REQUIRES_REVIEW),
        "route_eligibility_suspicious": _gate(counts.get(ISSUE_ROUTE_SUSPICIOUS, 0), 0, city_slug, ISSUE_ROUTE_SUSPICIOUS),
    }
    failed = [name for name, gate in gates.items() if gate["status"] == "critical"]
    return {
        "status": "critical" if failed else "pass",
        "hard_gates_enabled": bool(settings.data_quality_hard_gates_enabled),
        "blocks_publication": False,
        "failed_gates": failed,
        "gates": gates,
    }


def _counts(db: Session, city_id: int) -> dict[str, int]:
    rows = db.query(DataQualityIssue.issue_type).filter(
        DataQualityIssue.city_id == city_id,
        DataQualityIssue.status.in_(tuple(OPEN_STATUSES)),
    ).all()
    return {issue_type: sum(1 for (row_type,) in rows if row_type == issue_type) for (issue_type,) in rows}


def _gate(value: int, threshold: int, city_slug: str, issue_type: str) -> dict[str, object]:
    status = "critical" if value > threshold else "pass"
    return {
        "value": value,
        "threshold": threshold,
        "status": status,
        "issue_filter": {"city_slug": city_slug, "issue_type": issue_type, "status": "open"},
    }
