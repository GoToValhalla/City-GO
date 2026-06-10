from __future__ import annotations

from functools import reduce


LIMITS = {
    "coffee": 2,
    "cafe": 2,
    "food": 2,
    "restaurant": 2,
    "walk": 3,
    "park": 2,
    "culture": 3,
    "museum": 3,
    "gallery": 3,
    "evening": 2,
    "bar": 2,
    "pub": 2,
}


def can_use_category(category: str, used: dict[str, int]) -> bool:
    normalized = normalize_category(category)
    return used.get(normalized, 0) < LIMITS.get(normalized, 2)


def add_category(category: str, used: dict[str, int]) -> dict[str, int]:
    normalized = normalize_category(category)
    return {**used, normalized: used.get(normalized, 0) + 1}


def category_distribution(points: list[object]) -> dict[str, int]:
    return reduce(_add_point_category, points, {})


def normalize_category(category: str | None) -> str:
    return str(category or "").strip().casefold()


def _add_point_category(acc: dict[str, int], point: object) -> dict[str, int]:
    category = normalize_category(getattr(point, "category", ""))
    return {**acc, category: acc.get(category, 0) + 1}
