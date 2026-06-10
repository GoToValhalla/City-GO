"""
FastAPI-зависимости для доступа к БД: одна сессия на запрос, закрытие в finally.
"""

from collections.abc import Generator

from db.session import SessionLocal


def get_db() -> Generator:
    """Выдаёт SQLAlchemy Session и гарантирует db.close() после обработки запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
