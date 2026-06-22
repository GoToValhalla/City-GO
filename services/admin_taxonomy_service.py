"""Backend-driven taxonomy for admin UI controls."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.place import Place

_LABELS: dict[str, str] = {
    "attraction": "Достопримечательность",
    "bar": "Бар",
    "beach": "Пляж",
    "cafe": "Кафе",
    "coffee": "Кофе",
    "culture": "Культура",
    "food": "Еда",
    "health": "Здоровье",
    "hotel": "Проживание",
    "museum": "Музей",
    "park": "Парк",
    "service": "Сервис",
    "transport": "Транспорт",
    "useful": "Полезное",
    "viewpoint": "Смотровая точка",
    "walk": "Прогулка",
}


def admin_category_taxonomy(db: Session, *, city_slug: str | None = None) -> list[dict[str, object]]:
    catalog = {row.code: row for row in db.query(Category).order_by(Category.code.asc()).all()}
    observed = _observed_counts(db, city_slug=city_slug)
    codes = sorted(set(catalog) | set(_LABELS) | set(observed))
    return [_category_payload(code, catalog.get(code), observed.get(code, 0)) for code in codes if code]


def _observed_counts(db: Session, *, city_slug: str | None = None) -> dict[str, int]:
    query = (
        db.query(func.lower(func.trim(Place.category)).label("code"), func.count(Place.id).label("count"))
        .filter(Place.category.is_not(None), func.trim(Place.category) != "")
    )
    if city_slug:
        query = query.join(City).filter(City.slug == city_slug)
    rows = query.group_by(func.lower(func.trim(Place.category))).all()
    return {str(row.code): int(row.count or 0) for row in rows if row.code}


def _category_payload(code: str, row: Category | None, observed_count: int) -> dict[str, object]:
    return {
        "code": code,
        "label": row.name if row is not None else _LABELS.get(code, code.replace("_", " ").title()),
        "is_active": bool(row.is_active) if row is not None else True,
        "is_route_eligible": bool(row.is_route_eligible) if row is not None else code not in {"health", "transport", "useful"},
        "is_catalog_visible": bool(row.is_catalog_visible) if row is not None else code not in {"health", "transport", "useful"},
        "is_default_enabled": bool(row.is_default_enabled) if row is not None else code in _LABELS,
        "is_observed": observed_count > 0,
        "observed_count": observed_count,
        "source": _source(row, observed_count),
    }


def _source(row: Category | None, observed_count: int) -> str:
    if row is not None and observed_count > 0:
        return "catalog+observed"
    if row is not None:
        return "catalog"
    return "observed"
