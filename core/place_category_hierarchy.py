"""Иерархия категорий и маппинг legacy/OSM -> канон."""

from __future__ import annotations

CATEGORY_HIERARCHY: dict[str, tuple[str, ...]] = {
    "food_drinks": ("coffee", "food", "bar"),
    "attractions": ("attraction", "museum", "walk"),
    "nature": ("park", "beach"),
    "lodging": ("hotel",),
    "shopping": ("shopping_mall",),
    "healthcare": ("pharmacy", "clinic", "hospital", "healthcare"),
    "finance": ("bank", "atm"),
    "transport": ("transport", "bus_stop", "parking"),
    "public_services": ("police", "toilets", "shelter", "information"),
    "services": ("service",),
}

CATEGORY_LABELS_RU: dict[str, str] = {
    "coffee": "Кофейня",
    "food": "Еда",
    "bar": "Бар",
    "walk": "Прогулка",
    "museum": "Музей",
    "attraction": "Достопримечательность",
    "beach": "Пляж",
    "park": "Парк",
    "hotel": "Проживание",
    "shopping_mall": "Торговый центр",
    "pharmacy": "Аптека",
    "clinic": "Клиника",
    "hospital": "Больница",
    "healthcare": "Медицина",
    "bank": "Банк",
    "atm": "Банкомат",
    "transport": "Транспорт",
    "bus_stop": "Остановка",
    "parking": "Парковка",
    "police": "Полиция",
    "toilets": "Туалет",
    "shelter": "Укрытие",
    "information": "Информация",
    "service": "Услуги",
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
    "mall": "shopping_mall",
    "shopping_centre": "shopping_mall",
    "shopping_center": "shopping_mall",
    "health": "healthcare",
    "medical": "healthcare",
    "public_transport": "transport",
    "stop": "bus_stop",
    "services": "service",
    "useful": "service",
}

ROUTE_EXCLUDED_CATEGORIES = frozenset({
    "hotel",
    "shopping_mall",
    "pharmacy",
    "clinic",
    "hospital",
    "healthcare",
    "bank",
    "atm",
    "transport",
    "bus_stop",
    "parking",
    "police",
    "toilets",
    "shelter",
    "information",
    "service",
})


def normalize_category_code(raw: str | None) -> str | None:
    if not raw:
        return None
    code = raw.strip().lower()
    return LEGACY_TO_CANONICAL.get(code, code)
