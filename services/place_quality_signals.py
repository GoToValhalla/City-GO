"""Shared place quality signals for publication and route gates."""

from __future__ import annotations

import re

from models.place import Place

PLACEHOLDER_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*культурн(?:ое|ый|ая)\s+место\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*место\s+для\s+прогулки\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*парк\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*пляж\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*osm\s+(node|way|relation)?\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*(unnamed|unknown|без\s+названия|место\s+без\s+названия)\s*$", re.IGNORECASE),
)

PLACEHOLDER_SQL_PATTERNS: tuple[str, ...] = (
    "Культурное место OSM %",
    "Культурный объект OSM %",
    "Место для прогулки OSM %",
    "Парк OSM %",
    "Пляж OSM %",
    "OSM %",
    "Unnamed%",
    "Unknown%",
    "Без названия%",
    "Место без названия%",
)


def is_placeholder_title(title: str | None) -> bool:
    """Return True when title is an auto-generated fallback, not a real POI name."""

    text = str(title or "").strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in PLACEHOLDER_TITLE_PATTERNS)


def has_high_quality_route_core(place: Place) -> bool:
    """Core quality gate for route publication and bulk selection."""

    return (
        not is_placeholder_title(getattr(place, "title", None))
        and getattr(place, "lat", None) is not None
        and getattr(place, "lng", None) is not None
        and not (float(getattr(place, "lat", 0.0) or 0.0) == 0.0 and float(getattr(place, "lng", 0.0) or 0.0) == 0.0)
        and bool(str(getattr(place, "category", "") or getattr(place, "canonical_category", "") or "").strip())
        and int(getattr(place, "quality_score", 0) or 0) >= 75
        and str(getattr(place, "quality_tier", "") or "").strip().lower() in {"gold", "silver", "high", "medium"}
    )
