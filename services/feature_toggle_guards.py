"""Проверки feature toggles перед выполнением функций."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.feature_toggle_service import is_toggle_enabled


def _deny(code: int, detail: str) -> None:
    raise HTTPException(status_code=code, detail=detail)


def assert_web_public(db: Session) -> None:
    if not is_toggle_enabled(db, "web_app_enabled", default=True):
        _deny(503, "Веб-приложение временно отключено")
    if is_toggle_enabled(db, "maintenance_mode", default=False):
        _deny(503, "Сервис на обслуживании. Попробуйте позже.")


def assert_ai_layer(db: Session) -> None:
    if not is_toggle_enabled(db, "ai_layer_enabled", default=True):
        _deny(503, "AI-функции временно отключены")


def assert_ai_recommendations(db: Session, *, city_slug: str | None = None) -> None:
    assert_ai_layer(db)
    if not is_toggle_enabled(db, "ai_retrieval_enabled", default=True):
        _deny(503, "AI retrieval отключён")
    if city_slug and not is_toggle_enabled(db, "ai_recommendations_enabled", scope="city", scope_id=city_slug, default=True):
        _deny(503, "AI-рекомендации отключены для этого города")


def assert_verification_enabled(db: Session) -> None:
    if not is_toggle_enabled(db, "place_verification_enabled", default=True):
        _deny(503, "Верификация мест отключена")


def assert_photo_moderation(db: Session) -> None:
    if not is_toggle_enabled(db, "photo_moderation_enabled", default=True):
        _deny(503, "Модерация фото отключена")


def assert_auto_import(db: Session) -> None:
    if not is_toggle_enabled(db, "auto_import_enabled", default=True):
        _deny(503, "Автоимпорт отключён")


def assert_auto_enrichment(db: Session, *, city_slug: str | None = None) -> None:
    if not is_toggle_enabled(db, "auto_enrichment_enabled", default=False):
        _deny(503, "Автообогащение отключено глобально")
    if city_slug and not is_toggle_enabled(db, "auto_enrichment_enabled", scope="city", scope_id=city_slug, default=False):
        _deny(503, "Автообогащение отключено для города")


def assert_city_import(db: Session, city_slug: str) -> None:
    assert_auto_import(db)
    if not is_toggle_enabled(db, "import_enabled", scope="city", scope_id=city_slug, default=True):
        _deny(503, "Импорт отключён для этого города")
