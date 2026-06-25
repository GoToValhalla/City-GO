from services.osm_import_taxonomy import category_from_osm_tags, unsupported_tag_reason


def test_place_of_worship_is_mapped_to_culture() -> None:
    assert category_from_osm_tags({"amenity": "place_of_worship", "building": "cathedral"}) == "culture"


def test_monastery_historic_tag_is_mapped_to_culture() -> None:
    assert category_from_osm_tags({"historic": "monastery"}) == "culture"


def test_cave_entrance_is_mapped_to_walk() -> None:
    assert category_from_osm_tags({"natural": "cave_entrance"}) == "walk"


def test_theme_park_is_mapped_to_park() -> None:
    assert category_from_osm_tags({"tourism": "theme_park"}) == "park"


def test_fast_food_is_mapped_to_food() -> None:
    assert category_from_osm_tags({"amenity": "fast_food"}) == "food"


def test_meaningful_unknown_osm_tag_gets_unsupported_reason() -> None:
    assert unsupported_tag_reason({"amenity": "unknown_local_value"}) == "unsupported_tag"
