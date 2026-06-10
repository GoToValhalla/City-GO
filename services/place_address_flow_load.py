"""Загрузка городов и coverage для address flow."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_address_coverage import city_address_report


def load_coverage(db: Session, city_slugs: list[str] | None = None) -> dict[str, Any]:
    cities = db.query(City).order_by(City.slug.asc()).all()
    if city_slugs:
        allowed = set(city_slugs)
        cities = [city for city in cities if city.slug in allowed]
    report: dict[str, Any] = {}
    for city in cities:
        places = db.query(Place).filter(Place.city_id == city.id).all()
        report[city.slug] = city_address_report(places)
    return report


def city_needs_recovery(city_report: dict[str, Any], *, include_generic: bool) -> bool:
    if int(city_report.get("without_address") or 0) > 0:
        return True
    return include_generic and int(city_report.get("generic_address_count") or 0) > 0
