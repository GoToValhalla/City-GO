"""Иерархия категорий и маппинг legacy/OSM → канон."""

from __future__ import annotations

# parent RU → subcategories (канон codes)
CATEGORY_HIERARCHY: dict[str, tuple[str, ...]] = {
    "food_drinks": ("coffee", "food", "bar"),
    "attractions": ("attraction", "museum", "walk"),
    "nature": ("park", "beach"),
    "lodging": ("hotel",),
    "service": ("service",),
}

CATEGORY_LABELS_RU: dict[str, str] = {
    "coffee": "Кофейня", "food": "Еда", "bar": "Бар", "walk": "Прогулка",
    "museum": "Музей", "attraction": "Достопримечательность", "beach": "Пляж",
    "park": "Парк", "hotel": "Проживание", "service": "Сервис",
}

LEGACY_TO_CANONICAL: dict[str, str] = {
    "cafe": "coffee",
    "coffee_shop": "coffee",
    "coffee": "coffee",
    "restaurant": "food",
    "fast_food": "food",
    "food_court": "food",
    "bakery": "food",
    "confectionery": "food",
    "ice_cream": "food",
    "pub": "bar",
    "culture": "museum",
    "gallery": "museum",
    "viewpoint": "attraction",
    "artwork": "attraction",
    "historic": "attraction",
    "nature": "walk",
    "natural": "walk",
    "useful": "service",
    "health": "service",
    "transport": "service",
    "information": "service",
    "toilets": "service",
    "atm": "service",
    "parking": "service",
    "shelter": "service",
    "bank": "service",
    "police": "service",
    "pharmacy": "service",
    "clinic": "service",
    "hospital": "service",
}

ROUTE_EXCLUDED_CATEGORIES = frozenset({"service", "hotel"})


def normalize_category_code(raw: str | None) -> str | None:
    if not raw:
        return None
    code = raw.strip().lower()
    return LEGACY_TO_CANONICAL.get(code, code)
