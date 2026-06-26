"""
Фабрика движка и сессий БД; URL и настройки — из core.config.settings.
"""

import models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings


def _engine_kwargs() -> dict[str, object]:
    if settings.database_url.startswith("sqlite"):
        return {}

    return {
        "pool_pre_ping": True,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout_seconds,
        "pool_recycle": settings.db_pool_recycle_seconds,
        "connect_args": {
            "connect_timeout": settings.db_pool_timeout_seconds,
            "options": (
                f"-c statement_timeout={settings.db_statement_timeout_ms} "
                f"-c lock_timeout={settings.db_lock_timeout_ms}"
            ),
        },
    }


engine = create_engine(settings.database_url, echo=False, **_engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)