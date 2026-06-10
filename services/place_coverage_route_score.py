"""Route-readiness scoring and feature detection for place coverage reports."""

from __future__ import annotations

from models.place import Place

REQUIRED_ROUTE_CATEGORIES = ("coffee", "food", "walk", "museum", "bar", "park")

_SEA_KEYWORDS = (
    "sea", "beach", "coast", "coastal", "seaside",
    "promenade", "waterfront", "embankment",
)


def route_features(places: list[Place]) -> list[str]:
    return ["sea"] if any(_has_sea_feature(p) for p in places) else []


def missing_route_categories(counts: dict[str, int]) -> list[str]:
    return [c for c in REQUIRED_ROUTE_CATEGORIES if counts.get(c, 0) == 0]


def route_ready_score(
    total: int,
    opening: int,
    duration: int,
    counts: dict[str, int],
) -> float:
    if total == 0:
        return 0.0
    missing = len(missing_route_categories(counts))
    category_score = 1 - missing / len(REQUIRED_ROUTE_CATEGORIES)
    data_score = (opening / total + duration / total) / 2
    return round(category_score * 0.6 + data_score * 0.4, 3)


def _has_sea_feature(place: Place) -> bool:
    text = " ".join(str(v or "") for v in (
        place.category, place.title, place.short_description, place.address,
    )).casefold()
    return any(kw in text for kw in _SEA_KEYWORDS)
