from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.place_schedule import PlaceSchedule
from schemas.admin import AdminCityCreateRequest
from schemas.admin_taxonomy import CategoryWrite
from services.admin_service import create_city_and_queue_import
from services.taxonomy_admin_service import create_category


@dataclass(frozen=True)
class CatalogCityCreate:
    payload: AdminCityCreateRequest
    actor: str


@dataclass(frozen=True)
class CatalogTaxonomyCreate:
    payload: CategoryWrite
    actor: str


@dataclass(frozen=True)
class CatalogScheduleWrite:
    place_id: int
    weekday: str
    open_time: time | None
    close_time: time | None
    is_closed: bool = False


def create_catalog_city(db: Session, command: CatalogCityCreate) -> City:
    """Delegate to the existing transaction-owning city/import setup."""

    return create_city_and_queue_import(db, command.payload, actor=command.actor)


def catalog_city(db: Session, city_id: int) -> City | None:
    return db.query(City).filter(City.id == city_id).first()


def create_catalog_category(db: Session, command: CatalogTaxonomyCreate) -> Category:
    """Delegate to the existing transaction-owning taxonomy writer."""

    return create_category(db, data=command.payload.model_dump(), actor=command.actor)


def catalog_category(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def write_catalog_schedule(db: Session, command: CatalogScheduleWrite) -> PlaceSchedule:
    """Upsert one Catalog-owned schedule row; caller owns the transaction."""

    row = db.query(PlaceSchedule).filter(
        PlaceSchedule.place_id == command.place_id,
        PlaceSchedule.weekday == command.weekday,
    ).first()
    if row is None:
        row = PlaceSchedule(place_id=command.place_id, weekday=command.weekday)
        db.add(row)
    row.open_time = command.open_time
    row.close_time = command.close_time
    row.is_closed = command.is_closed
    db.flush()
    return row


def catalog_schedule(db: Session, place_id: int) -> tuple[PlaceSchedule, ...]:
    rows = db.query(PlaceSchedule).filter(PlaceSchedule.place_id == place_id).order_by(
        PlaceSchedule.weekday, PlaceSchedule.id,
    ).all()
    return tuple(rows)
