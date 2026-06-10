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
    "cafe": "coffee", "culture": "museum", "viewpoint": "attraction",
    "useful": "service", "health": "service",
}

ROUTE_EXCLUDED_CATEGORIES = frozenset({"service", "hotel"})


def normalize_category_code(raw: str | None) -> str | None:
    if not raw:
        return None
    code = raw.strip().lower()
    return LEGACY_TO_CANONICAL.get(code, code)
