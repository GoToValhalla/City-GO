"""Выбор мест-кандидатов для address recovery."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_address_policy import needs_recovery


def recovery_candidates(
    db: Session,
    city_slug: str,
    limit: int,
    *,
    include_generic: bool,
) -> tuple[City, list[Place]]:
    city = db.query(City).filter(City.slug == city_slug).one()
    items = [
        place
        for place in db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
        if needs_recovery(place.address, place.category, include_generic=include_generic)
    ]
    return city, items[:limit]
