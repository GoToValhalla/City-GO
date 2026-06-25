from data.scripts import import_city_osm as legacy_import
from data.scripts import import_city_osm_v2 as coverage_import


def test_coverage_aware_import_installs_extended_profiles_and_taxonomy() -> None:
    coverage_import._install_coverage_taxonomy()

    tourist_filters = coverage_import.COVERAGE_AWARE_PROFILE_FILTERS["tourist_core"]

    assert ("amenity", "cafe|restaurant|place_of_worship|monastery") in tourist_filters
    assert ("building", "church|cathedral|monastery|chapel") in tourist_filters
    assert ("natural", "beach|water|wood|peak|cave_entrance|cave") in tourist_filters
    assert ("tourism", "attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park") in tourist_filters
    assert legacy_import.PROFILE_FILTERS is coverage_import.COVERAGE_AWARE_PROFILE_FILTERS
    assert legacy_import._category({"amenity": "place_of_worship", "building": "cathedral"}) == "culture"
    assert legacy_import._category({"natural": "cave_entrance"}) == "walk"


def test_coverage_aware_nature_profile_includes_day_trip_objects() -> None:
    nature_filters = coverage_import.COVERAGE_AWARE_PROFILE_FILTERS["nature_walk"]

    assert ("natural", "beach|water|wood|peak|cave_entrance|cave") in nature_filters
    assert ("waterway", "waterfall") in nature_filters
    assert ("tourism", "viewpoint|information|attraction") in nature_filters
