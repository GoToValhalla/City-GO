"""Сводка readiness по всем городам."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from services.city_readiness.score import compute_city_readiness


def list_cities_readiness(db: Session, *, limit: int = 100) -> list[dict[str, object]]:
    cities = db.query(City).order_by(City.name.asc()).limit(limit).all()
    rows: list[dict[str, object]] = []
    for city in cities:
        payload = compute_city_readiness(db, city_slug=city.slug)
        if payload is not None:
            rows.append(payload)
    return rows
