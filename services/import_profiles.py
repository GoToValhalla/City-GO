"""Production import profiles used by City GO data jobs.

The values are high-level coverage tokens, not raw Overpass clauses. Raw OSM key/value
selection still lives in importer code, while this registry documents which semantic
families are allowed in production profiles.
"""

IMPORT_PROFILES: dict[str, tuple[str, ...]] = {
    "tourist_core": (
        "tourism",
        "historic",
        "heritage",
        "wikidata",
        "wikipedia",
        "museum",
        "gallery",
        "attraction",
        "viewpoint",
        "place_of_worship",
        "church",
        "cathedral",
        "monastery",
        "chapel",
        "castle",
        "ruins",
        "theme_park",
        "park",
        "beach",
        "promenade",
        "cafe",
        "restaurant",
    ),
    "tourist_core_strict": (
        "tourism",
        "historic",
        "heritage",
        "wikidata",
        "wikipedia",
        "museum",
        "gallery",
        "attraction",
        "viewpoint",
        "landmark",
        "park",
    ),
    "heritage_religious": (
        "place_of_worship",
        "monastery",
        "church",
        "cathedral",
        "chapel",
        "temple",
        "synagogue",
        "mosque",
        "heritage",
        "historic",
        "wikidata",
        "wikipedia",
    ),
    "nature_region": (
        "viewpoint",
        "natural",
        "leisure",
        "nature_reserve",
        "national_park",
        "beach",
        "waterfall",
        "peak",
        "cave_entrance",
        "camp_site",
        "picnic_site",
    ),
    "food_and_coffee": (
        "cafe",
        "restaurant",
        "fast_food",
        "food_court",
        "bakery",
        "confectionery",
        "coffee",
        "tea",
        "ice_cream",
        "bar",
        "pub",
    ),
    "food_quality": (
        "cafe",
        "restaurant",
        "bar",
        "pub",
        "marketplace",
        "bakery",
        "confectionery",
        "coffee",
        "tea",
    ),
    "nature_walk": (
        "park",
        "garden",
        "beach",
        "viewpoint",
        "natural",
        "leisure",
        "walk",
        "cave_entrance",
        "waterfall",
        "peak",
        "wood",
        "nature_reserve",
    ),
    "service_infra": ("toilets", "parking", "drinking_water", "shelter", "information"),
    "transport_hub": ("airport", "railway_station", "bus_station", "ferry_terminal"),
    "useful_services": ("toilets", "pharmacy", "atm", "parking", "bus_stop", "shelter"),
    "manual_seed": ("curated", "wikidata", "osm", "official_source"),
    "full_osm": ("debug_only",),
}

PROFILE_ROUTE_LAYER: dict[str, str] = {
    "tourist_core": "tourist_catalog",
    "tourist_core_strict": "tourist_catalog",
    "heritage_religious": "tourist_catalog",
    "nature_region": "tourist_catalog",
    "nature_walk": "tourist_catalog",
    "food_and_coffee": "food_layer",
    "food_quality": "food_layer",
    "service_infra": "service_layer",
    "useful_services": "service_layer",
    "transport_hub": "transport_layer",
    "manual_seed": "tourist_catalog",
}


def import_profile_tags(profile: str) -> tuple[str, ...]:
    if profile not in IMPORT_PROFILES:
        raise ValueError(f"unknown import profile: {profile}")
    return IMPORT_PROFILES[profile]


def production_profile(profile: str) -> bool:
    return profile in IMPORT_PROFILES and profile != "full_osm"


def profile_layer(profile: str) -> str:
    return PROFILE_ROUTE_LAYER.get(profile, "tourist_catalog")
