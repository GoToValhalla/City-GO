from __future__ import annotations

from typing import Any

from core.place_category_hierarchy import CATEGORY_LABELS_RU
from services.place_lineage import safe_lineage_map
from services.place_public_quality import first_image, hours_text, quality_payload

RAW_PREFIXES = ("amenity:", "osm:", "ref:", "shop:", "tourism:", "historic:", "railway:", "highway:")
EMPTY_STRINGS = {"", "null", "undefined", "none", "nan"}


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in EMPTY_STRINGS:
        return None
    lowered = text.lower()
    if any(lowered.startswith(prefix) for prefix in RAW_PREFIXES) or lowered.endswith("_core"):
        return None
    return text.replace("bus_stop", "").strip() or None


def category_payload(category: str | None) -> dict[str, str | None]:
    clean = clean_text(category)
    if clean is None:
        return {"slug": None, "label": "Место"}
    normalized = clean.lower().replace(" ", "_")
    return {"slug": normalized, "label": CATEGORY_LABELS_RU.get(normalized, normalized.replace("_", " ").title())}


def valid_coordinates(lat: object, lng: object) -> tuple[float | None, float | None, bool]:
    try:
        lat_float, lng_float = float(lat), float(lng)
    except (TypeError, ValueError):
        return None, None, True
    suspicious = lat_float == 0.0 and lng_float == 0.0
    valid = -90 <= lat_float <= 90 and -180 <= lng_float <= 180
    return (lat_float, lng_float, suspicious or not valid) if valid else (None, None, True)


def sanitize_change(field: str, value: object) -> object:
    if field in {"title", "name", "short_description", "description", "address", "category"}:
        cleaned = clean_text(value)
        if cleaned is None:
            raise ValueError("UNSAFE_VALUE")
        return cleaned
    if field in {"lat", "lng", "latitude", "longitude"}:
        number = float(value)  # raises ValueError by design
        low, high = (-90, 90) if field in {"lat", "latitude"} else (-180, 180)
        if not low <= number <= high:
            raise ValueError("INVALID_COORDINATES")
        return number
    if field == "average_visit_duration_minutes":
        number = int(value)
        if number <= 0 or number > 1440:
            raise ValueError("INVALID_DURATION")
        return number
    return value


def public_place_payload(place: Any, image_urls: list[str] | None = None) -> dict[str, object]:
    category = category_payload(getattr(place, "canonical_category", None) or getattr(place, "category", None))
    lat, lng, coord_degraded = valid_coordinates(getattr(place, "lat", None), getattr(place, "lng", None))
    lineage = safe_lineage_map(getattr(place, "lineage", {}) or {})
    return {
        "id": getattr(place, "id"),
        "slug": getattr(place, "slug"),
        "name": clean_text(getattr(place, "title", None)) or category["label"],
        "title": clean_text(getattr(place, "title", None)) or category["label"],
        "category": category["slug"] or "place",
        "category_label": category["label"],
        "category_info": category,
        "description": clean_text(getattr(place, "short_description", None)),
        "short_description": clean_text(getattr(place, "short_description", None)),
        "address": clean_text(getattr(place, "address", None)),
        "coordinates": {"lat": lat, "lng": lng},
        "lat": lat,
        "lng": lng,
        "image_url": first_image(place, image_urls),
        "image_urls": image_urls or None,
        "photo_urls": image_urls or None,
        "opening_hours": hours_text(getattr(place, "opening_hours", None)),
        "operating_hours": hours_text(getattr(place, "opening_hours", None)),
        "average_visit_duration_minutes": getattr(place, "average_visit_duration_minutes", None),
        "price_level": getattr(place, "price_level", None),
        "dog_friendly": bool(getattr(place, "dog_friendly", False)),
        "family_friendly": bool(getattr(place, "family_friendly", False)),
        "indoor": bool(getattr(place, "indoor", False)),
        "outdoor": bool(getattr(place, "outdoor", False)),
        "phone": clean_text(getattr(place, "phone", None)),
        "website": clean_text(getattr(place, "website", None)),
        "data_quality": quality_payload(place, lineage, coord_degraded),
    }
