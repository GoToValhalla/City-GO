"""Нормализация категорий мест к канонической таксономии."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.place_category_hierarchy import LEGACY_TO_CANONICAL, normalize_category_code
from core.place_taxonomy import PLACE_CATEGORIES
from models.city import City
from models.place import Place


def normalize_city_categories(db: Session, *, city_slug: str, apply: bool = True) -> dict[str, int]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise ValueError(f"Город не найден: {city_slug}")
    places = db.query(Place).filter(Place.city_id == city.id).all()
    scanned = updated = skipped = 0
    for place in places:
        scanned += 1
        canon = normalize_category_code(place.category)
        if canon is None or canon == place.category:
            if canon and canon in PLACE_CATEGORIES:
                skipped += 1
            continue
        if canon not in PLACE_CATEGORIES:
            skipped += 1
            continue
        if apply:
            place.category = canon
            db.add(place)
        updated += 1
    if apply and updated:
        db.commit()
    return {"scanned": scanned, "updated": updated, "skipped": skipped, "legacy_map": LEGACY_TO_CANONICAL}
