from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Глобальный OSM taxonomy contract для импорта и coverage assurance.
# Здесь не должно быть city-specific заплаток: новые теги должны решать класс POI,
# который повторится в следующих городах.

HERITAGE_AMENITIES = {"place_of_worship", "monastery"}
HERITAGE_BUILDINGS = {"church", "cathedral", "monastery", "chapel", "synagogue", "mosque", "temple"}
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
    "wayside_shrine",
    "wayside_cross",
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
NATURE_WALK = {"water", "wood", "peak", "cave_entrance", "cave", "volcano", "cliff", "ridge", "spring"}
WATERWAY_WALK = {"waterfall", "river", "stream"}
TRANSPORT_ATTRACTIONS = {"funicular", "cable_car", "gondola", "monorail", "tram"}

PLACE_LAYER_TOURIST = "tourist_catalog"
PLACE_LAYER_FOOD = "food_layer"
PLACE_LAYER_SERVICE = "service_layer"
PLACE_LAYER_TRANSPORT = "transport_layer"
PLACE_LAYER_EVIDENCE = "admin_evidence_only"

ROUTE_POLICY_CITY_WALKING = "city_walking"
ROUTE_POLICY_FOOD_STOP = "food_stop"
ROUTE_POLICY_DAY_TRIP = "day_trip"
ROUTE_POLICY_REGION = "region_scope"
ROUTE_POLICY_INFRA_ONLY = "infra_only"
ROUTE_POLICY_TRANSFER_ONLY = "transfer_only"
ROUTE_POLICY_NEVER = "never"

CITY_WALKING_SCOPE_TYPES = {"city_core", "city_district", "tourist_core", "food_area", "nature_nearby"}
REGIONAL_SCOPE_TYPES = {"day_trip", "nature_area", "corridor", "must_have_anchor", "region_pack", "satellite_town"}

EXPLICIT_GARBAGE_TAGS: dict[str, set[str]] = {
    "amenity": {
        "atm",
        "bank",
        "pharmacy",
        "clinic",
        "hospital",
        "police",
        "bureau_de_change",
        "fuel",
        "post_office",
    },
    "highway": {"bus_stop", "platform"},
    "public_transport": {"platform", "stop_position"},
    "shop": {"supermarket", "convenience", "laundry", "hairdresser", "mobile_phone"},
}

CRITICAL_SERVICE_TAGS: dict[str, set[str]] = {
    "amenity": {"toilets", "parking", "drinking_water", "shelter"},
    "tourism": {"information"},
}

TRANSPORT_HUB_TAGS: dict[str, set[str]] = {
    "aeroway": {"aerodrome", "terminal"},
    "railway": {"station"},
    "amenity": {"bus_station", "ferry_terminal"},
    "public_transport": {"station"},
}


@dataclass(frozen=True)
class PlaceLayerClassification:
    layer: str
    route_policy: str
    tourist_eligible: bool
    is_route_eligible: bool
    route_exclusion_reason: str | None = None


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

    if _has_tag_match(tags, EXPLICIT_GARBAGE_TAGS):
        return "health" if amenity in {"pharmacy", "clinic", "hospital"} or tags.get("healthcare") else "useful"

    if _has_tag_match(tags, CRITICAL_SERVICE_TAGS) or tags.get("healthcare"):
        return "health" if tags.get("healthcare") else "useful"

    if _has_tag_match(tags, TRANSPORT_HUB_TAGS):
        return "transport"

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

    if tourism == "theme_park" or leisure in PARK_LEISURE or attraction == "amusement_ride":
        return "park"

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

    if natural == "beach" or leisure == "beach_resort":
        return "beach"

    if natural in NATURE_WALK or waterway in WATERWAY_WALK or boundary == "national_park":
        return "walk"

    if leisure in {"marina", "promenade"} or highway in {"pedestrian", "footway"} and place in {"promenade"}:
        return "walk"

    if railway in TRANSPORT_ATTRACTIONS or aerialway in TRANSPORT_ATTRACTIONS or route in TRANSPORT_ATTRACTIONS:
        return "transport"

    return None


def classify_osm_place(
    tags: dict[str, Any],
    *,
    profile: str | None = None,
    scope_type: str | None = None,
    transport_required: bool = False,
) -> PlaceLayerClassification:
    """Returns the storage layer and route policy for an imported OSM object.

    The rule is deliberately stricter than category mapping. A bank or pharmacy can be
    observed and stored as evidence, but it must not contaminate the tourist catalogue
    or city walking route candidate pool.
    """

    normalized_profile = (profile or "").strip().lower()
    normalized_scope_type = (scope_type or "").strip().lower()

    if _has_tag_match(tags, EXPLICIT_GARBAGE_TAGS):
        return PlaceLayerClassification(
            layer=PLACE_LAYER_EVIDENCE,
            route_policy=ROUTE_POLICY_NEVER,
            tourist_eligible=False,
            is_route_eligible=False,
            route_exclusion_reason="not_tourist_poi",
        )

    if normalized_profile in {"service_infra", "useful_services"} or _has_tag_match(tags, CRITICAL_SERVICE_TAGS):
        return PlaceLayerClassification(
            layer=PLACE_LAYER_SERVICE,
            route_policy=ROUTE_POLICY_INFRA_ONLY,
            tourist_eligible=False,
            is_route_eligible=False,
            route_exclusion_reason="service_infrastructure_layer",
        )

    if normalized_profile == "transport_hub" or _has_tag_match(tags, TRANSPORT_HUB_TAGS):
        return PlaceLayerClassification(
            layer=PLACE_LAYER_TRANSPORT,
            route_policy=ROUTE_POLICY_TRANSFER_ONLY,
            tourist_eligible=False,
            is_route_eligible=False,
            route_exclusion_reason="transport_hub_layer",
        )

    category = category_from_osm_tags(tags)
    if category in {"food", "cafe", "market"} or normalized_profile in {"food_quality", "food_and_coffee"}:
        return PlaceLayerClassification(
            layer=PLACE_LAYER_FOOD,
            route_policy=ROUTE_POLICY_FOOD_STOP,
            tourist_eligible=True,
            is_route_eligible=not transport_required and normalized_scope_type not in REGIONAL_SCOPE_TYPES,
            route_exclusion_reason="transport_required_scope" if transport_required else None,
        )

    if transport_required or normalized_scope_type in REGIONAL_SCOPE_TYPES:
        return PlaceLayerClassification(
            layer=PLACE_LAYER_TOURIST,
            route_policy=ROUTE_POLICY_DAY_TRIP if normalized_scope_type != "region_pack" else ROUTE_POLICY_REGION,
            tourist_eligible=True,
            is_route_eligible=False,
            route_exclusion_reason="transport_required_scope",
        )

    return PlaceLayerClassification(
        layer=PLACE_LAYER_TOURIST,
        route_policy=ROUTE_POLICY_CITY_WALKING,
        tourist_eligible=bool(category),
        is_route_eligible=bool(category),
        route_exclusion_reason=None if category else "unsupported_tourist_taxonomy",
    )


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


def _has_tag_match(tags: dict[str, Any], rules: dict[str, set[str]]) -> bool:
    for key, allowed_values in rules.items():
        value = tags.get(key)
        if isinstance(value, str) and value in allowed_values:
            return True
    return False
