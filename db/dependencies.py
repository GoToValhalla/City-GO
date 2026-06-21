"""
FastAPI-зависимости для доступа к БД: одна сессия на запрос, rollback при ошибке, закрытие в finally.
"""

from collections.abc import Generator
from typing import Any

from db.session import SessionLocal


def get_db() -> Generator[Any, None, None]:
    """Выдаёт SQLAlchemy Session и гарантирует cleanup после обработки запроса."""
    db = SessionLocal()
    try:
        yield db
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()