"""Проверка feature toggles перед генерацией маршрута."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.feature_toggle_service import is_toggle_enabled


def assert_route_generation_allowed(db: Session, *, city_slug: str | None = None) -> None:
    if not is_toggle_enabled(db, "route_planning_engine_enabled", default=True):
        raise HTTPException(status_code=503, detail="Движок маршрутов отключён")
    if not is_toggle_enabled(db, "route_generation_enabled", default=True):
        raise HTTPException(status_code=503, detail="Генерация маршрутов временно отключена")
    if city_slug and not is_toggle_enabled(db, "route_generation_enabled", scope="city", scope_id=city_slug, default=True):
        raise HTTPException(status_code=503, detail="Генерация маршрутов отключена для этого города")
