from __future__ import annotations

from functools import reduce

CANONICAL_ROUTE_CATEGORIES = frozenset(
    {
        "food",
        "cafe",
        "restaurant",
        "bar",
        "museum",
        "culture",
        "park",
        "walk",
        "viewpoint",
        "landmark",
        "history",
        "shopping",
        "service",
        "utility",
        "transport",
        "health",
    }
)

CATEGORY_ALIASES = {
    "coffee": "cafe",
    "espresso": "cafe",
    "tea": "cafe",
    "pub": "bar",
    "biergarten": "bar",
    "fast_food": "restaurant",
    "dining": "restaurant",
    "eatery": "restaurant",
    "attraction": "landmark",
    "sight": "landmark",
    "sightseeing": "landmark",
    "monument": "landmark",
    "historic": "history",
    "heritage": "history",
    "gallery": "culture",
    "theatre": "culture",
    "theater": "culture",
    "promenade": "walk",
    "outdoor": "walk",
    "beach": "walk",
    "sea": "walk",
    "shopping_mall": "shopping",
    "mall": "shopping",
    "shop": "shopping",
    "generic_shop": "shopping",
    "pharmacy": "health",
    "apteka": "health",
    "clinic": "health",
    "hospital": "health",
    "bank": "service",
    "atm": "service",
    "toilet": "utility",
    "toilets": "utility",
    "parking": "transport",
    "fuel": "transport",
    "bus_stop": "transport",
    "stop": "transport",
    "public_transport": "transport",
}

FOOD_ROUTE_CATEGORIES = frozenset({"food", "cafe", "restaurant", "bar"})
CORE_WALK_CATEGORIES = frozenset({"museum", "culture", "park", "walk", "viewpoint", "landmark", "history"})
ROUTE_JUNK_CATEGORIES = frozenset({"service", "utility", "transport", "health"})

LIMITS = {
    "food": 2,
    "cafe": 2,
    "restaurant": 2,
    "bar": 2,
    "museum": 3,
    "culture": 3,
    "park": 3,
    "walk": 3,
    "viewpoint": 3,
    "landmark": 3,
    "history": 3,
    "shopping": 1,
}

MAX_FOOD_FAMILY_POINTS = 2


def can_use_category(category: str, used: dict[str, int]) -> bool:
    normalized = normalize_category(category)
    if is_route_junk_category(normalized):
        return False
    if is_food_category(normalized) and food_family_count(used) >= MAX_FOOD_FAMILY_POINTS:
        return False
    return used.get(normalized, 0) < LIMITS.get(normalized, 2)


def add_category(category: str, used: dict[str, int]) -> dict[str, int]:
    normalized = normalize_category(category)
    return {**used, normalized: used.get(normalized, 0) + 1}


def category_distribution(points: list[object]) -> dict[str, int]:
    return reduce(_add_point_category, points, {})


def normalize_category(category: str | None) -> str:
    value = str(category or "").strip().casefold().replace("-", "_").replace(" ", "_")
    return CATEGORY_ALIASES.get(value, value)


def is_food_category(category: str | None) -> bool:
    return normalize_category(category) in FOOD_ROUTE_CATEGORIES


def is_core_walk_category(category: str | None) -> bool:
    return normalize_category(category) in CORE_WALK_CATEGORIES


def is_route_junk_category(category: str | None) -> bool:
    return normalize_category(category) in ROUTE_JUNK_CATEGORIES


def food_family_count(used: dict[str, int]) -> int:
    return sum(int(used.get(category, 0) or 0) for category in FOOD_ROUTE_CATEGORIES)


def _add_point_category(acc: dict[str, int], point: object) -> dict[str, int]:
    category = normalize_category(getattr(point, "category", ""))
    return {**acc, category: acc.get(category, 0) + 1}
