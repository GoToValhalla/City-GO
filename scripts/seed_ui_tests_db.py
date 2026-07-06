"""Seed a tiny local SQLite dataset for Playwright UI smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from db.base import Base
from db.session import engine
from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.place import Place
from models.place_merge_review import ReviewItem


CITY = {"slug": "zelenogradsk", "name": "Зеленоградск", "region": "Калининградская область", "country": "Россия", "timezone": "Europe/Kaliningrad", "center_lat": 54.9601, "center_lng": 20.4753, "launch_status": "published", "is_active": True, "quality_status": "ready", "readiness_score": 90}
CATEGORIES = (("museum", "Музей"), ("cafe", "Кафе"), ("park", "Парк"))
PLACES = (
    ("museum-kurort", "Музей курортной истории", "museum", 54.9608, 20.4759),
    ("cafe-center", "Кафе у вокзала", "cafe", 54.9589, 20.4768),
    ("queen-louise-park", "Парк королевы Луизы", "park", 54.9619, 20.4728),
    ("degraded-card", "Карточка на проверке", "museum", 54.9622, 20.4731),
)


def _upsert_city(db: Session) -> City:
    city = db.query(City).filter(City.slug == CITY["slug"]).first() or City(slug=str(CITY["slug"]), name=str(CITY["name"]))
    for key, value in CITY.items():
        setattr(city, key, value)
    db.add(city)
    db.flush()
    return city


def _upsert_category(db: Session, code: str, name: str) -> Category:
    category = db.query(Category).filter(Category.code == code).first() or Category(code=code, name=name)
    category.name = name
    category.is_active = True
    category.is_catalog_visible = True
    category.is_searchable = True
    category.is_route_eligible = True
    category.route_policy = "allowed"
    db.add(category)
    db.flush()
    return category


def _upsert_place(db: Session, city: City, categories: dict[str, Category], row: tuple[str, str, str, float, float]) -> None:
    slug, title, code, lat, lng = row
    place = db.query(Place).filter(Place.city_id == city.id, Place.slug == slug).first() or Place(city_id=city.id, slug=slug, title=title, lat=lat, lng=lng)
    category = categories[code]
    for key, value in _place_payload(title, category, lat, lng).items():
        setattr(place, key, value)
    if slug == "degraded-card":
        place.short_description = None
        place.address = None
        place.completeness_score = 0
    db.add(place)


def _place_payload(title: str, category: Category, lat: float, lng: float) -> dict[str, object]:
    return {
        "title": title, "lat": lat, "lng": lng, "category_id": category.id,
        "category": category.code, "canonical_category": category.code, "address": "Зеленоградск, центр",
        "short_description": f"{title} — тестовое публичное место для локальных UI smoke-проверок.",
        "status": "active", "lifecycle_status": "active", "publication_status": "published",
        "is_active": True, "is_published": True, "is_visible_in_catalog": True,
        "is_route_eligible": True, "is_searchable": True, "quality_score": 80,
        "completeness_score": 30, "confidence_score": 8, "existence_confidence_level": "high", "verification_status": "verified",
    }


def _seed_review(db: Session, city: City) -> None:
    place = db.query(Place).filter(Place.city_id == city.id, Place.slug == "museum-kurort").one()
    db.add(ReviewItem(
        place_id=place.id, proposed_diff={"address": {"current": place.address, "proposed": "Зеленоградск, Курортный проспект", "reason": "LOW_CONFIDENCE_SCORE"}},
        status="pending", created_by="ui-seed", place_version_at_creation=place.version,
        source="EXTERNAL_API_ENRICHED", confidence=0.5, reason="LOW_CONFIDENCE_SCORE",
    ))


def _reset_local_schema() -> None:
    if "ui_tests_local.db" not in settings.database_url:
        raise RuntimeError("Refusing to reset a non-ui-tests database.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def main() -> None:
    _reset_local_schema()
    db = SessionLocal()
    try:
        city = _upsert_city(db)
        categories = {code: _upsert_category(db, code, name) for code, name in CATEGORIES}
        [_upsert_place(db, city, categories, row) for row in PLACES]
        _seed_review(db, city)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
