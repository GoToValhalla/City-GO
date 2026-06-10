"""Inline city settings через feature toggles API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from services.feature_toggle_catalog import CITY_TOGGLES
from services.feature_toggle_service import is_toggle_enabled, list_city_toggles, update_toggle

INLINE_KEYS = tuple(t["key"] for t in CITY_TOGGLES)


def city_settings_payload(db: Session, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    toggles = list_city_toggles(db, city_slug)
    return {
        "city_id": city.id, "city_slug": city.slug, "city_name": city.name,
        "launch_status": city.launch_status, "is_active": city.is_active,
        "toggles": toggles,
    }


def update_city_toggle(db: Session, *, city_slug: str, key: str, value: bool, actor: str, reason: str | None) -> None:
    if key not in INLINE_KEYS:
        raise ValueError(f"Неизвестная настройка города: {key}")
    update_toggle(db, key=key, scope="city", scope_id=city_slug, value_bool=value, actor=actor, reason=reason)
