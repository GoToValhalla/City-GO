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
    "useful_services": ("toilets", "pharmacy", "atm", "parking", "bus_stop", "shelter"),
    "full_osm": ("debug_only",),
}


def import_profile_tags(profile: str) -> tuple[str, ...]:
    if profile not in IMPORT_PROFILES:
        raise ValueError(f"unknown import profile: {profile}")
    return IMPORT_PROFILES[profile]


def production_profile(profile: str) -> bool:
    return profile in IMPORT_PROFILES and profile != "full_osm"
