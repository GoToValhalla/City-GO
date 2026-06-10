"""Сводные метрики админки. DAU/MAU — после event pipeline."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.route_build_event import RouteBuildEvent
from services.product_event_service import build_product_metrics


def build_metrics_summary(db: Session) -> dict[str, object]:
    built = int(db.query(func.count(RouteBuildEvent.id)).scalar() or 0)
    failed = int(db.query(func.count(RouteBuildEvent.id)).filter(RouteBuildEvent.has_warnings.is_(True)).scalar() or 0)
    avg_stops = float(db.query(func.avg(RouteBuildEvent.total_places)).scalar() or 0)
    product = build_product_metrics(db)
    return {
        "dau": 0, "mau": 0,
        "routes_built": built, "routes_failed": failed, "avg_route_stops": round(avg_stops, 1),
        **product,
        "data_collection_note": "DAU/MAU — после auth events. Маршруты и данные — из product_events + route_build_events.",
    }
