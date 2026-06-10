from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import SessionLocal
from telegram_bot.services.context_store import database_ops
from telegram_bot.services.context_store.types import SelectedCity, UserAddress, UserLocation

T = TypeVar("T")


def save_location(user_id: int, lat: float, lng: float) -> bool:
    return _write(
        lambda db: database_ops.save_location_row(db, user_id, lat, lng)
    )


def get_location(user_id: int) -> UserLocation | None:
    return _read(lambda db: database_ops.read_location_row(db, user_id))


def save_address(user_id: int, raw_address: str) -> bool:
    return _write(
        lambda db: database_ops.save_address_row(db, user_id, raw_address)
    )


def get_address(user_id: int) -> UserAddress | None:
    return _read(lambda db: database_ops.read_address_row(db, user_id))


def save_route(user_id: int, route: dict[str, object]) -> bool:
    return _write(lambda db: database_ops.save_route_row(db, user_id, route))


def get_route(user_id: int) -> dict[str, object] | None:
    return _read(lambda db: database_ops.read_route_row(db, user_id))


def save_city(user_id: int, slug: str) -> bool:
    return _write(lambda db: database_ops.save_city_row(db, user_id, slug))


def get_city(user_id: int) -> SelectedCity | None:
    return _read(lambda db: database_ops.read_city_row(db, user_id))


def reset_context(user_id: int) -> bool:
    return _write(lambda db: database_ops.reset_context_row(db, user_id))


def _write(operation: Callable[[Session], None]) -> bool:
    try:
        with SessionLocal() as db:
            operation(db)
        return True
    except SQLAlchemyError:
        return False


def _read(operation: Callable[[Session], T | None]) -> T | None:
    try:
        with SessionLocal() as db:
            return operation(db)
    except SQLAlchemyError:
        return None
