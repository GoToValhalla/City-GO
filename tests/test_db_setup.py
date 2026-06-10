"""Применение alembic-миграций к тестовой SQLite БД."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def resolve_test_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("sqlite"):
        return url
    return "sqlite:///:memory:?cache=shared"


def apply_alembic_migrations(database_url: str) -> None:
    root = Path(__file__).resolve().parents[1]
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        cfg = Config(str(root / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev


def create_test_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url)


def rebind_session_local(engine: Engine) -> sessionmaker:
    import db.session as session_module

    session_module.engine = engine
    session_module.SessionLocal.configure(bind=engine)
    return session_module.SessionLocal
