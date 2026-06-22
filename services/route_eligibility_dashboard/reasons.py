"""Коды причин для Eligibility Dashboard."""

from __future__ import annotations

from models.city import City
from models.place import Place

from services.place_quality_score import compute_place_quality_score, is_low_quality
from services.place_quality_signals import is_placeholder_title
from services.route_eligibility import evaluate_place_route_eligibility

_DASHBOARD_CODES = frozenset({
    "forbidden_category", "no_coordinates", "inactive_place", "unpublished_place",
    "hidden_place", "placeholder_title", "no_photo", "no_address", "no_description",
    "low_quality", "other",
})

_REASON_MAP = {
    "missing_city_id": "other",
    "city_inactive": "other",
    "city_not_published": "other",
    "place_inactive": "inactive_place",
    "place_status_not_active": "inactive_place",
    "place_not_published": "unpublished_place",
    "place_not_visible_in_catalog": "hidden_place",
    "route_eligible_false": "other",
    "placeholder_title": "placeholder_title",
    "missing_coordinates": "no_coordinates",
    "invalid_coordinates": "no_coordinates",
}


def dashboard_reasons(place: Place, *, city: City | None = None) -> list[str]:
    codes: list[str] = []
    for raw in evaluate_place_route_eligibility(place, city=city).reasons:
        if raw.startswith("forbidden_category:"):
            codes.append("forbidden_category")
        else:
            codes.append(_REASON_MAP.get(raw, "other"))
    if is_placeholder_title(getattr(place, "title", None)):
        codes.append("placeholder_title")
    if not place.image_url:
        codes.append("no_photo")
    if not place.address or not str(place.address).strip():
        codes.append("no_address")
    if not place.short_description or not str(place.short_description).strip():
        codes.append("no_description")
    if is_low_quality(compute_place_quality_score(place)):
        codes.append("low_quality")
    return _dedupe(codes)


def primary_reason(reasons: list[str]) -> str:
    for code in (
        "forbidden_category", "placeholder_title", "no_coordinates", "inactive_place",
        "unpublished_place", "hidden_place", "low_quality", "no_photo", "no_address",
        "no_description", "other",
    ):
        if code in reasons:
            return code
    return "other"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in _DASHBOARD_CODES and item not in seen:
            seen.add(item)
            out.append(item)
    return out