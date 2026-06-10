IMPORT_PROFILES: dict[str, tuple[str, ...]] = {
    "tourist_core": (
        "tourism", "historic", "museum", "gallery", "attraction", "viewpoint",
        "park", "beach", "promenade", "cafe", "restaurant",
    ),
    "food_and_coffee": ("cafe", "restaurant", "fast_food", "bakery", "ice_cream", "bar"),
    "nature_walk": ("park", "garden", "beach", "viewpoint", "natural", "leisure", "walk"),
    "useful_services": ("toilets", "pharmacy", "atm", "parking", "bus_stop", "shelter"),
    "full_osm": ("debug_only",),
}


def import_profile_tags(profile: str) -> tuple[str, ...]:
    if profile not in IMPORT_PROFILES:
        raise ValueError(f"unknown import profile: {profile}")
    return IMPORT_PROFILES[profile]


def production_profile(profile: str) -> bool:
    return profile in IMPORT_PROFILES and profile != "full_osm"
