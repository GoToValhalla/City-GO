"""Краткая сводка очереди верификации для админки."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.place import Place


def verification_queue_summary(db: Session) -> dict[str, int]:
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    queue = db.query(Place).filter(Place.verification_status.in_(("needs_recheck", "unverified", "moved")))
    return {
        "queue_total": queue.count(),
        "needs_recheck": db.query(Place).filter(Place.verification_status == "needs_recheck").count(),
        "unverified": db.query(Place).filter(Place.verification_status == "unverified").count(),
        "low_confidence": db.query(Place).filter(Place.existence_confidence_level.in_(("low", "unknown"))).count(),
        "verified_today": db.query(Place).filter(Place.verified_at >= start).count(),
    }
