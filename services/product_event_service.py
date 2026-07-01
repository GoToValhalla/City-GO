"""Product events для метрик."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func
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
    events = _event_counts_since(db, week)
    today_events = _event_counts_since(db, today)
    routes_ok = events.get("route_generation_success", 0)
    routes_fail = events.get("route_generation_failed", 0)
    total = routes_ok + routes_fail
    places = _place_counts(db)
    return {
        "routes_today": today_events.get("route_generation_success", 0) + today_events.get("route_generation_failed", 0),
        "routes_week": total,
        "routes_failed_week": routes_fail,
        "route_success_rate": round(routes_ok / total * 100, 1) if total else None,
        "places_total": places["total"],
        "places_published": places["published"],
        "places_no_photo": places["no_photo"],
        "places_no_address": places["no_address"],
        "places_no_description": places["no_description"],
        "imports_ok_week": events.get("import_finished", 0),
        "imports_fail_week": events.get("import_failed", 0),
        "enrichment_ok_week": events.get("enrichment_finished", 0),
        "ai_requests_week": events.get("ai_request_success", 0) + events.get("ai_request_failed", 0),
    }


def _event_counts_since(db: Session, since: datetime) -> dict[str, int]:
    rows = (
        db.query(ProductEvent.event_type, func.count(ProductEvent.id))
        .filter(ProductEvent.created_at >= since)
        .group_by(ProductEvent.event_type)
        .all()
    )
    return {str(event_type): int(count or 0) for event_type, count in rows}


def _place_counts(db: Session) -> dict[str, int]:
    row = db.query(
        func.count(Place.id),
        func.sum(case((Place.is_published.is_(True), 1), else_=0)),
        func.sum(case((Place.image_url.is_(None), 1), else_=0)),
        func.sum(case((Place.address.is_(None), 1), else_=0)),
        func.sum(case((Place.short_description.is_(None), 1), else_=0)),
    ).one()
    return {
        "total": int(row[0] or 0),
        "published": int(row[1] or 0),
        "no_photo": int(row[2] or 0),
        "no_address": int(row[3] or 0),
        "no_description": int(row[4] or 0),
    }


def _count(db: Session, event_type: str, since: datetime) -> int:
    return int(db.query(func.count(ProductEvent.id)).filter(
        ProductEvent.event_type == event_type, ProductEvent.created_at >= since,
    ).scalar() or 0)
