from __future__ import annotations

COVERAGE_PROFILE_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "tourist_core_strict": [
        ("tourism", "attraction|museum|gallery|viewpoint|artwork|zoo|aquarium|theme_park"),
        ("historic", None),
        ("heritage", None),
        ("building", "church|cathedral|monastery|chapel|synagogue|mosque"),
        ("leisure", "park|garden|nature_reserve|marina|promenade"),
        ("natural", "beach|peak|cave_entrance|cave|cliff"),
        ("waterway", "waterfall"),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "heritage_religious": [
        ("amenity", "place_of_worship|monastery"),
        ("historic", "monastery|church|cathedral|ruins|castle|fort|tower|archaeological_site|memorial|monument|wayside_shrine|wayside_cross"),
        ("building", "church|cathedral|monastery|chapel|synagogue|mosque"),
        ("heritage", None),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "nature_region": [
        ("leisure", "park|garden|nature_reserve|marina|promenade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge|spring"),
        ("waterway", "waterfall|river|stream"),
        ("tourism", "viewpoint|information|attraction|camp_site|picnic_site"),
        ("boundary", "national_park"),
        ("heritage", None),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "food_quality": [
        ("amenity", "cafe|restaurant|bar|pub|marketplace"),
        ("shop", "bakery|confectionery|coffee|tea|ice_cream|deli|cheese|pastry|marketplace"),
        ("cuisine", None),
    ],
    "service_infra": [
        ("amenity", "toilets|parking|drinking_water|shelter"),
        ("tourism", "information"),
    ],
}
