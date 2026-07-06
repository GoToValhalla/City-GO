from __future__ import annotations

import re
from dataclasses import dataclass

DESTINATION_TYPES = {
    "city", "region", "natural_region", "national_park",
    "tourist_cluster", "route_corridor", "remote_area",
}
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


@dataclass(frozen=True)
class ValidationIssue(Exception):
    message: str


def normalize_slug(value: str) -> str:
    normalized = re.sub(r"[-_\s]+", "-", value.strip().lower())
    return re.sub(r"[^a-z0-9-]", "", normalized).strip("-")


def validate_slug(value: str) -> str:
    slug = normalize_slug(value)
    if not slug or not SLUG_RE.fullmatch(slug):
        raise ValidationIssue("Slug должен содержать только латиницу, цифры и дефисы")
    return slug


def validate_destination_type(value: str) -> str:
    if value not in DESTINATION_TYPES:
        raise ValidationIssue("Тип направления не поддерживается")
    return value


def validate_coordinates(lat: float | None, lng: float | None) -> None:
    if lat is not None and not -90 <= float(lat) <= 90:
        raise ValidationIssue("Широта должна быть в диапазоне -90..90")
    if lng is not None and not -180 <= float(lng) <= 180:
        raise ValidationIssue("Долгота должна быть в диапазоне -180..180")


def validate_bbox(value: dict[str, object] | None) -> dict[str, float] | None:
    if value is None:
        return None
    try:
        bbox = {
            "south": float(value.get("south") or value.get("min_lat")),
            "west": float(value.get("west") or value.get("min_lng")),
            "north": float(value.get("north") or value.get("max_lat")),
            "east": float(value.get("east") or value.get("max_lng")),
        }
    except (AttributeError, TypeError, ValueError):
        raise ValidationIssue("BBox должен содержать south, west, north, east") from None
    if not (-90 <= bbox["south"] < bbox["north"] <= 90):
        raise ValidationIssue("BBox: south должен быть меньше north в диапазоне -90..90")
    if not (-180 <= bbox["west"] < bbox["east"] <= 180):
        raise ValidationIssue("BBox: west должен быть меньше east в диапазоне -180..180")
    return bbox


def validate_required_text(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationIssue(f"{label} обязательно")
    return cleaned
