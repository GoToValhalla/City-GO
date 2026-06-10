from sqlalchemy.orm import Session

from models.telegram_user_context import TelegramUserContext
from telegram_bot.services.context_store.types import SelectedCity, UserAddress, UserLocation


def save_location_row(db: Session, user_id: int, lat: float, lng: float) -> None:
    row = _get_or_create(db, user_id)
    row.last_lat = lat
    row.last_lng = lng
    db.commit()


def read_location_row(db: Session, user_id: int) -> UserLocation | None:
    row = db.get(TelegramUserContext, user_id)
    if row is None or row.last_lat is None or row.last_lng is None:
        return None
    return {"lat": float(row.last_lat), "lng": float(row.last_lng)}


def save_address_row(db: Session, user_id: int, raw_address: str) -> None:
    row = _get_or_create(db, user_id)
    row.raw_address = raw_address
    db.commit()


def read_address_row(db: Session, user_id: int) -> UserAddress | None:
    row = db.get(TelegramUserContext, user_id)
    if row is None or row.raw_address is None:
        return None
    return {"raw_address": row.raw_address}


def save_route_row(
    db: Session,
    user_id: int,
    route: dict[str, object],
) -> None:
    row = _get_or_create(db, user_id)
    row.route_state = route
    db.commit()


def read_route_row(db: Session, user_id: int) -> dict[str, object] | None:
    row = db.get(TelegramUserContext, user_id)
    if row is None or not isinstance(row.route_state, dict):
        return None
    return row.route_state


def save_city_row(db: Session, user_id: int, slug: str) -> None:
    row = _get_or_create(db, user_id)
    row.selected_city_slug = slug
    db.commit()


def read_city_row(db: Session, user_id: int) -> SelectedCity | None:
    row = db.get(TelegramUserContext, user_id)
    if row is None or not row.selected_city_slug:
        return None
    return {"slug": row.selected_city_slug}


def reset_context_row(db: Session, user_id: int) -> None:
    row = db.get(TelegramUserContext, user_id)
    if row is None:
        return
    row.last_lat = None
    row.last_lng = None
    row.raw_address = None
    row.route_state = None
    row.selected_city_slug = None
    db.commit()


def _get_or_create(db: Session, user_id: int) -> TelegramUserContext:
    row = db.get(TelegramUserContext, user_id)
    if row is not None:
        return row

    created = TelegramUserContext(user_id=user_id)
    db.add(created)
    return created
