"""Краткая сводка очереди верификации для админки."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.place import Place


def verification_queue_summary(db: Session) -> dict[str, int]:
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    row = db.query(
        func.sum(case((Place.verification_status.in_(("needs_recheck", "unverified", "moved")), 1), else_=0)),
        func.sum(case((Place.verification_status == "needs_recheck", 1), else_=0)),
        func.sum(case((Place.verification_status == "unverified", 1), else_=0)),
        func.sum(case((Place.existence_confidence_level.in_(("low", "unknown")), 1), else_=0)),
        func.sum(case((Place.verified_at >= start, 1), else_=0)),
    ).one()
    return {
        "queue_total": int(row[0] or 0),
        "needs_recheck": int(row[1] or 0),
        "unverified": int(row[2] or 0),
        "low_confidence": int(row[3] or 0),
        "verified_today": int(row[4] or 0),
    }
