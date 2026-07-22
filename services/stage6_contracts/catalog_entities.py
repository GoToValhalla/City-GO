from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.place_schedule import PlaceSchedule
from schemas.admin import AdminCityCreateRequest
from schemas.admin_taxonomy import CategoryWrite
from services.admin_service import create_city_and_queue_import
from services.taxonomy_admin_service import create_category

# Единственный канонический набор дней недели, используемый везде в
# кодовой базе (services/open_now_service.py::get_weekday_code,
# models/place_schedule.py, scripts/seed_minimal_data.py). Не является
# новым бизнес-правилом — фиксирует уже существующий контракт.
_VALID_WEEKDAYS: frozenset[str] = frozenset({"mon", "tue", "wed", "thu", "fri", "sat", "sun"})
# Порядок для календарной сортировки (mon..sun), используется вместо
# лексикографического ORDER BY weekday.
_WEEKDAY_ORDER: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


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
    """Upsert one Catalog-owned schedule row; caller owns the transaction.

    Race-safe: uses a single atomic INSERT ... ON CONFLICT DO UPDATE against
    the database-level uq_place_schedules_place_weekday unique index
    (models/place_schedule.py, migrations/versions/e2c4b6a8d0f3_...), instead
    of a SELECT-then-INSERT, so two concurrent transactions writing the same
    (place_id, weekday) cannot both insert -- the loser's INSERT is
    atomically converted into the UPDATE branch by the database itself, at
    the same commit that would otherwise raise a unique-violation. This
    function flushes but never commits; the caller owns transaction
    boundaries and rollback.
    """

    if command.weekday not in _VALID_WEEKDAYS:
        raise ValueError(
            f"Invalid weekday {command.weekday!r}; expected one of {sorted(_VALID_WEEKDAYS)}."
        )

    values = {
        "place_id": command.place_id,
        "weekday": command.weekday,
        "open_time": command.open_time,
        "close_time": command.close_time,
        "is_closed": command.is_closed,
    }
    update_values = {
        "open_time": command.open_time,
        "close_time": command.close_time,
        "is_closed": command.is_closed,
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = pg_insert(PlaceSchedule).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[PlaceSchedule.place_id, PlaceSchedule.weekday],
            set_=update_values,
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(PlaceSchedule).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[PlaceSchedule.place_id, PlaceSchedule.weekday],
            set_=update_values,
        )
    else:
        raise ValueError(f"Unsupported place_schedules database dialect: {dialect}")

    db.execute(statement)
    db.flush()
    # populate_existing() is required here: the raw Core INSERT ... ON
    # CONFLICT DO UPDATE bypasses the ORM unit-of-work, so if this row's
    # PlaceSchedule instance is already in the session's identity map from
    # an earlier query in this same transaction, a plain query would
    # return that same stale Python object without refreshing its
    # attributes from the row this statement just updated.
    row = db.query(PlaceSchedule).populate_existing().filter(
        PlaceSchedule.place_id == command.place_id,
        PlaceSchedule.weekday == command.weekday,
    ).one()
    return row


def catalog_schedule(db: Session, place_id: int) -> tuple[PlaceSchedule, ...]:
    """Return this place's schedule rows in calendar order (mon..sun), id as
    the deterministic secondary key within a weekday."""

    weekday_order = case(
        {weekday: position for position, weekday in enumerate(_WEEKDAY_ORDER)},
        value=PlaceSchedule.weekday,
    )
    rows = db.query(PlaceSchedule).filter(PlaceSchedule.place_id == place_id).order_by(
        weekday_order, PlaceSchedule.id,
    ).all()
    return tuple(rows)
