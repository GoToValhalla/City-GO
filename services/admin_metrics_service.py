"""Сводные метрики админки. DAU/MAU — после event pipeline."""

from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.route_build_event import RouteBuildEvent
from services.product_event_service import build_product_metrics


def build_metrics_summary(db: Session) -> dict[str, object]:
    route_row = db.query(
        func.count(RouteBuildEvent.id),
        func.sum(case((RouteBuildEvent.has_warnings.is_(True), 1), else_=0)),
        func.avg(RouteBuildEvent.total_places),
    ).one()
    built = int(route_row[0] or 0)
    failed = int(route_row[1] or 0)
    avg_stops = float(route_row[2] or 0)
    product = build_product_metrics(db)
    return {
        "dau": 0, "mau": 0,
        "routes_built": built, "routes_failed": failed, "avg_route_stops": round(avg_stops, 1),
        **product,
        "data_collection_note": "DAU/MAU — после auth events. Маршруты и данные — из product_events + route_build_events.",
    }
