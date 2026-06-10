from __future__ import annotations

from typing import Any

from schemas.merged_context import MergedContext
from services.place_runtime_defaults import effective_opening_hours, effective_visit_duration
from services.scoring_service import ScoredPlace

WALK_INTERESTS = {"walk", "park", "outdoor", "sea"}
PLACEHOLDER_ADDRESSES = {
    "адрес не указан",
    "нет адреса",
    "unknown",
    "-",
}
COMPACT_WALK_DURATIONS = {
    "walk": 18,
    "park": 22,
    "outdoor": 18,
    "attraction": 20,
    "viewpoint": 15,
    "culture": 25,
    "museum": 30,
    "gallery": 25,
    "coffee": 20,
    "cafe": 20,
}


def route_point_from_scored(scored: ScoredPlace, ctx: MergedContext, point_cls: type) -> object:
    place = scored.place
    validation = _validation(place)
    return point_cls(
        place_id=str(place.id),
        title=_clean_text(getattr(place, "title", None)),
        address=_address(place),
        image_url=_image_url(place),
        short_description=_clean_text(getattr(place, "short_description", None)),
        source=getattr(place, "source", None),
        city_slug=_city_slug(place),
        lat=float(place.lat),
        lng=float(place.lng),
        score=float(scored.score),
        category=str(place.category or ""),
        visit_minutes=_visit_minutes(place, ctx),
        opening_hours=effective_opening_hours(place),
        validation=validation,
        price_level=getattr(place, "price_level", None),
        scoring_breakdown=dict(getattr(scored, "breakdown", {}) or {}),
    )


def visit_minutes_for_scored(scored: ScoredPlace, ctx: MergedContext) -> int:
    return _visit_minutes(scored.place, ctx)


def _visit_minutes(place: object, ctx: MergedContext) -> int:
    category = str(getattr(place, "category", "") or "").strip().casefold()
    dwell = effective_visit_duration(place)
    if _is_walking_route(ctx):
        dwell = min(dwell, COMPACT_WALK_DURATIONS.get(category, 25))
    return max(1, int(float(dwell) * float(ctx.pace_multiplier)))


def _image_url(place: object) -> str | None:
    public_url = _clean_url(getattr(place, "public_image_url", None))
    if public_url:
        return public_url
    legacy_url = _clean_url(getattr(place, "image_url", None))
    if legacy_url:
        return legacy_url
    return None


def _address(place: object) -> str:
    address = _clean_address(getattr(place, "address", None))
    if address:
        return address
    return "Адрес уточняется"


def _clean_address(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    normalized = text.casefold().strip()
    if normalized in PLACEHOLDER_ADDRESSES:
        return None
    if "координаты" in normalized:
        return None
    return text


def _clean_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_url(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return None


def _is_walking_route(ctx: MergedContext) -> bool:
    interests = {str(item).strip().casefold() for item in getattr(ctx, "interests", []) or []}
    return not interests or bool(interests & WALK_INTERESTS)


def _validation(place: object) -> dict[str, Any] | None:
    raw = getattr(place, "validation", None)
    return raw if isinstance(raw, dict) else None


def _city_slug(place: object) -> str | None:
    city = getattr(place, "city", None)
    return getattr(city, "slug", None)
