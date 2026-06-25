from __future__ import annotations

from typing import Any

# Глобальный OSM taxonomy contract для импорта и coverage assurance.
# Здесь не должно быть city-specific заплаток: новые теги должны решать класс POI,
# который повторится в следующих городах.

HERITAGE_AMENITIES = {"place_of_worship", "monastery"}
HERITAGE_BUILDINGS = {"church", "cathedral", "monastery", "chapel", "synagogue", "mosque"}
HERITAGE_HISTORIC = {
    "yes",
    "monastery",
    "church",
    "cathedral",
    "ruins",
    "castle",
    "fort",
    "tower",
    "archaeological_site",
    "memorial",
    "monument",
}
FOOD_AMENITIES = {"restaurant", "fast_food", "bar", "pub", "food_court", "biergarten"}
CAFE_AMENITIES = {"cafe"}
MARKET_AMENITIES = {"marketplace"}
FOOD_SHOPS = {"bakery", "confectionery", "ice_cream", "deli", "cheese", "pastry"}
COFFEE_SHOPS = {"coffee", "tea"}
PARK_LEISURE = {
    "park",
    "garden",
    "nature_reserve",
    "playground",
    "theme_park",
    "amusement_arcade",
}
NATURE_WALK = {"water", "wood", "peak", "cave_entrance", "cave", "volcano", "cliff", "ridge"}
WATERWAY_WALK = {"waterfall", "river", "stream"}
TRANSPORT_ATTRACTIONS = {"funicular", "cable_car", "gondola", "monorail", "tram"}


def category_from_osm_tags(tags: dict[str, Any]) -> str | None:
    """Maps raw OSM tags to City GO canonical category codes.

    This mapper is intentionally deterministic. It is used by import coverage tests,
    source reconciliation and import normalization so that one new city does not need
    another local taxonomy patch for every monastery, cave, market or viewpoint.
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
    railway = tags.get("railway")
    aerialway = tags.get("aerialway")
    route = tags.get("route")
    highway = tags.get("highway")
    man_made = tags.get("man_made")
    boundary = tags.get("boundary")
    place = tags.get("place")

    if amenity in CAFE_AMENITIES or shop in COFFEE_SHOPS:
        return "cafe"

    if amenity in FOOD_AMENITIES or shop in FOOD_SHOPS:
        return "food"

    if amenity in MARKET_AMENITIES or shop == "marketplace":
        return "market"

    if tourism == "museum":
        return "museum"

    if tourism == "viewpoint" or man_made in {"tower", "lighthouse"}:
        return "viewpoint"

    if (
        tourism in {"attraction", "gallery", "artwork", "zoo", "aquarium"}
        or amenity in HERITAGE_AMENITIES
        or building in HERITAGE_BUILDINGS
        or historic in HERITAGE_HISTORIC
        or tags.get("heritage")
        or tags.get("wikidata")
        or tags.get("wikipedia")
    ):
        return "culture"

    if tourism == "theme_park" or leisure in PARK_LEISURE or attraction == "amusement_ride":
        return "park"

    if natural == "beach" or leisure == "beach_resort":
        return "beach"

    if natural in NATURE_WALK or waterway in WATERWAY_WALK or boundary == "national_park":
        return "walk"

    if leisure in {"marina", "promenade"} or highway in {"pedestrian", "footway"} and place in {"promenade"}:
        return "walk"

    if railway in TRANSPORT_ATTRACTIONS or aerialway in TRANSPORT_ATTRACTIONS or route in TRANSPORT_ATTRACTIONS:
        return "transport"

    if amenity in {"toilets", "atm", "parking", "shelter", "bank", "police"}:
        return "useful"

    if amenity in {"pharmacy", "clinic", "hospital"}:
        return "health"

    return None


def unsupported_tag_reason(tags: dict[str, Any]) -> str | None:
    """Returns a stable gap reason for unsupported but meaningful OSM tags."""

    if category_from_osm_tags(tags):
        return None
    meaningful_keys = {
        "amenity",
        "tourism",
        "historic",
        "natural",
        "leisure",
        "building",
        "heritage",
        "wikidata",
        "wikipedia",
        "railway",
        "aerialway",
        "waterway",
        "route",
        "boundary",
    }
    if any(key in tags for key in meaningful_keys):
        return "unsupported_tag"
    return "source_absent"
