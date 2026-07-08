"""Shared place quality signals for publication and route gates."""

from __future__ import annotations

import re

from models.place import Place

PLACEHOLDER_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*культурн(?:ое|ый|ая)\s+(?:место|объект)\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*место\s+для\s+прогулки\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*place\s+for\s+walk\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*парк\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*пляж\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*[a-zа-я ]+\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*osm\s+(node|way|relation)?\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*(node|way|relation)\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*unnamed\s+(poi|place|point)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(unnamed|unknown|без\s+названия|место\s+без\s+названия)\s*$", re.IGNORECASE),
    # Generic/generated fallback labels (provider-side placeholder naming,
    # not real POI names — e.g. "место для отдыха 134567", "точка 123").
    re.compile(r"^\s*место\s+для\s+отдыха\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*точка\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*объект\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*poi\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*tourism\s+object\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
)

PLACEHOLDER_SQL_PATTERNS: tuple[str, ...] = (
    "Культурное место OSM %",
    "Культурный объект OSM %",
    "Место для прогулки OSM %",
    "Place for walk OSM %",
    "Парк OSM %",
    "Пляж OSM %",
    "% OSM %",
    "OSM %",
    "Node %",
    "Way %",
    "Relation %",
    "Unnamed%",
    "Unknown%",
    "Без названия%",
    "Место без названия%",
    "Место для отдыха %",
    "Точка %",
    "Объект %",
    "POI %",
    "Tourism object %",
)


def is_placeholder_title(title: str | None) -> bool:
    """Return True when title is an auto-generated fallback, not a real POI name."""

    text = str(title or "").strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in PLACEHOLDER_TITLE_PATTERNS)


def has_high_quality_route_core(place: Place, *, computed_score: int | None = None) -> bool:
    """Core quality gate for route publication and bulk selection."""

    score = _quality_score(place, computed_score=computed_score)
    return (
        not is_placeholder_title(getattr(place, "title", None))
        and getattr(place, "lat", None) is not None
        and getattr(place, "lng", None) is not None
        and not (float(getattr(place, "lat", 0.0) or 0.0) == 0.0 and float(getattr(place, "lng", 0.0) or 0.0) == 0.0)
        and bool(str(getattr(place, "category", "") or getattr(place, "canonical_category", "") or "").strip())
        and score >= 75
        and str(getattr(place, "quality_tier", "") or "").strip().lower() in {"gold", "silver", "high", "medium"}
    )


def _quality_score(place: Place, *, computed_score: int | None) -> int:
    if computed_score is not None:
        return computed_score
    from services.place_quality_score import compute_place_quality_score

    return compute_place_quality_score(place)
