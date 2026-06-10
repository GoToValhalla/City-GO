from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.session import SessionLocal


def check_database_ready() -> tuple[bool, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
        return True, "ok"
    except SQLAlchemyError as exc:
        return False, exc.__class__.__name__
