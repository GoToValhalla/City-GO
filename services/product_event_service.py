"""Product events для метрик."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.place import Place
from models.product_event import ProductEvent


def record_event(
    db: Session,
    *,
    event_type: str,
    payload: dict[str, Any] | None = None,
    city_slug: str | None = None,
    place_id: int | None = None,
    user_id: str | None = None,
    commit: bool = True,
) -> ProductEvent:
    row = ProductEvent(
        event_type=event_type, payload=payload or {},
        city_slug=city_slug, place_id=place_id, user_id=user_id,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def count_events_since(db: Session, event_type: str, *, days: int = 7) -> int:
    since = datetime.utcnow() - timedelta(days=days)
    return int(
        db.query(func.count(ProductEvent.id))
        .filter(ProductEvent.event_type == event_type, ProductEvent.created_at >= since)
        .scalar() or 0
    )


def build_product_metrics(db: Session) -> dict[str, object]:
    today = datetime.utcnow() - timedelta(days=1)
    week = datetime.utcnow() - timedelta(days=7)
    routes_ok = _count(db, "route_generation_success", week)
    routes_fail = _count(db, "route_generation_failed", week)
    total = routes_ok + routes_fail
    return {
        "routes_today": _count(db, "route_generation_success", today) + _count(db, "route_generation_failed", today),
        "routes_week": total,
        "routes_failed_week": routes_fail,
        "route_success_rate": round(routes_ok / total * 100, 1) if total else None,
        "places_total": db.query(Place).count(),
        "places_published": db.query(Place).filter(Place.is_published.is_(True)).count(),
        "places_no_photo": db.query(Place).filter(Place.image_url.is_(None)).count(),
        "places_no_address": db.query(Place).filter(Place.address.is_(None)).count(),
        "places_no_description": db.query(Place).filter(Place.short_description.is_(None)).count(),
        "imports_ok_week": _count(db, "import_finished", week),
        "imports_fail_week": _count(db, "import_failed", week),
        "enrichment_ok_week": _count(db, "enrichment_finished", week),
        "ai_requests_week": _count(db, "ai_request_success", week) + _count(db, "ai_request_failed", week),
    }


def _count(db: Session, event_type: str, since: datetime) -> int:
    return int(db.query(func.count(ProductEvent.id)).filter(
        ProductEvent.event_type == event_type, ProductEvent.created_at >= since,
    ).scalar() or 0)
