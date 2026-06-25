from __future__ import annotations

from typing import Any


HERITAGE_BUILDINGS = {"church", "cathedral", "monastery", "chapel"}
HERITAGE_HISTORIC = {"yes", "monastery", "church", "cathedral", "ruins", "castle"}
FOOD_AMENITIES = {"restaurant", "fast_food", "bar", "pub", "food_court"}
PARK_LEISURE = {"park", "garden", "nature_reserve", "playground", "theme_park", "amusement_arcade"}
NATURE_WALK = {"water", "wood", "peak", "cave_entrance", "cave"}


def category_from_osm_tags(tags: dict[str, Any]) -> str | None:
    """Maps raw OSM tags to City GO canonical category codes.

    This mapper is intentionally small and deterministic. It is used as the
    shared contract for import coverage tests and the import pipeline can call it
    instead of re-implementing tag logic in several scripts.
    """

    amenity = tags.get("amenity")
    tourism = tags.get("tourism")
    leisure = tags.get("leisure")
    natural = tags.get("natural")
    historic = tags.get("historic")
    shop = tags.get("shop")
    building = tags.get("building")
    attraction = tags.get("attraction")
    waterway = tags.get("waterway")

    if amenity == "cafe" or shop in {"coffee", "tea"}:
        return "cafe"

    if amenity in FOOD_AMENITIES or shop in {"bakery", "confectionery", "ice_cream"}:
        return "food"

    if tourism == "museum":
        return "museum"

    if (
        tourism in {"attraction", "gallery", "artwork"}
        or amenity in {"place_of_worship", "monastery"}
        or building in HERITAGE_BUILDINGS
        or historic in HERITAGE_HISTORIC
        or tags.get("heritage")
    ):
        return "culture"

    if tourism == "viewpoint":
        return "viewpoint"

    if tourism == "theme_park" or leisure in PARK_LEISURE or attraction == "amusement_ride":
        return "park"

    if natural == "beach":
        return "beach"

    if natural in NATURE_WALK or waterway == "waterfall":
        return "walk"

    if amenity in {"toilets", "atm", "parking", "shelter", "bank", "police"}:
        return "useful"

    if amenity in {"pharmacy", "clinic", "hospital"}:
        return "health"

    return None


def unsupported_tag_reason(tags: dict[str, Any]) -> str | None:
    """Returns a stable gap reason for unsupported but meaningful OSM tags."""

    if category_from_osm_tags(tags):
        return None
    if any(key in tags for key in ("amenity", "tourism", "historic", "natural", "leisure", "building")):
        return "unsupported_tag"
    return "source_absent"
