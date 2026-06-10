"""Поиск города по slug и алиасам."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City


def resolve_city_by_slug(db: Session, slug: str) -> City | None:
    city = db.query(City).filter(City.slug == slug).first()
    if city is not None:
        return city
    rows = db.query(City).filter(City.slug_aliases.isnot(None)).all()
    return next((c for c in rows if slug in (c.slug_aliases or [])), None)
