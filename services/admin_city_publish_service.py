"""Публикация города для публичного каталога и маршрутов."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from services.admin_audit_service import write_admin_audit_log

PUBLISHED = "published"


def publish_city_for_users(
    db: Session,
    *,
    city_slug: str,
    actor: str,
    reason: str | None = None,
    country: str | None = None,
    timezone: str | None = None,
) -> City:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise ValueError(f"Город не найден: {city_slug}")
    old = {
        "launch_status": city.launch_status,
        "is_active": city.is_active,
        "country": city.country,
        "timezone": city.timezone,
    }
    city.launch_status = PUBLISHED
    city.is_active = True
    if country:
        city.country = country
    if timezone:
        city.timezone = timezone
    write_admin_audit_log(
        db,
        actor=actor,
        action="publish_city",
        entity_type="city",
        entity_id=city.id,
        old_value=old,
        new_value={
            "launch_status": city.launch_status,
            "is_active": city.is_active,
            "country": city.country,
            "timezone": city.timezone,
        },
        reason=reason or "Город опубликован для сайта и маршрутов",
    )
    db.commit()
    db.refresh(city)
    return city
