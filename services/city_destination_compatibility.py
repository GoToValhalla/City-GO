"""City ↔ Destination compatibility layer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.destination import Destination


def get_destination_by_slug(db: Session, slug: str) -> Destination | None:
    return db.query(Destination).filter(Destination.slug == slug).first()


def get_destination_by_id(db: Session, destination_id: int) -> Destination | None:
    return db.query(Destination).filter(Destination.id == destination_id).first()


def get_destination_for_city(db: Session, city: City) -> Destination | None:
    row = db.query(Destination).filter(Destination.legacy_city_id == city.id).first()
    if row is not None:
        return row
    return db.query(Destination).filter(Destination.slug == city.slug).first()


def resolve_city_slug_to_destination(db: Session, city_slug: str) -> Destination | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    return get_destination_for_city(db, city)


def resolve_destination_to_city_slug(db: Session, destination: Destination) -> str | None:
    if destination.legacy_city_id is not None:
        city = db.query(City).filter(City.id == destination.legacy_city_id).first()
        if city is not None:
            return city.slug
    city = db.query(City).filter(City.slug == destination.slug).first()
    return city.slug if city else None


def resolve_destination_to_city_id(db: Session, destination: Destination) -> int | None:
    if destination.legacy_city_id is not None:
        return destination.legacy_city_id
    city = db.query(City).filter(City.slug == destination.slug).first()
    return city.id if city else None
