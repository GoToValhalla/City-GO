from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from models.telegram_user_context import TelegramUserContext
from telegram_bot.services.context_store import database_ops


def _session_factory() -> sessionmaker:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[TelegramUserContext.__table__])
    return sessionmaker(bind=engine)


def test_database_store_roundtrip() -> None:
    factory = _session_factory()

    with factory() as db:
        database_ops.save_location_row(db, 42, 54.9, 20.4)
        database_ops.save_address_row(db, 42, "Зеленоградск")
        database_ops.save_route_row(db, 42, {"route_id": "r1", "points": []})

    with factory() as db:
        assert database_ops.read_location_row(db, 42) == {"lat": 54.9, "lng": 20.4}
        assert database_ops.read_address_row(db, 42) == {"raw_address": "Зеленоградск"}
        assert database_ops.read_route_row(db, 42) == {"route_id": "r1", "points": []}


def test_database_store_reset_clears_context_fields() -> None:
    factory = _session_factory()

    with factory() as db:
        database_ops.save_location_row(db, 43, 54.9, 20.4)
        database_ops.save_address_row(db, 43, "Зеленоградск")
        database_ops.save_route_row(db, 43, {"route_id": "r1", "points": []})
        database_ops.reset_context_row(db, 43)

    with factory() as db:
        assert database_ops.read_location_row(db, 43) is None
        assert database_ops.read_address_row(db, 43) is None
        assert database_ops.read_route_row(db, 43) is None
