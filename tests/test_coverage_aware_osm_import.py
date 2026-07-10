from data.scripts import import_city_osm as legacy_import
from data.scripts import import_city_osm_v2 as coverage_import
from services.import_profiles import IMPORT_PROFILES
from services.osm_import_taxonomy import classify_osm_place


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


def test_useful_services_profile_no_longer_fetches_parking_or_bank() -> None:
    (useful_services_filter,) = coverage_import.COVERAGE_AWARE_PROFILE_FILTERS["useful_services"]
    key, value_pattern = useful_services_filter
    fetched_values = value_pattern.split("|")

    assert key == "amenity"
    assert "parking" not in fetched_values
    assert "bank" not in fetched_values


def test_useful_services_profile_keeps_remaining_tags_unchanged() -> None:
    (useful_services_filter,) = coverage_import.COVERAGE_AWARE_PROFILE_FILTERS["useful_services"]
    _, value_pattern = useful_services_filter
    fetched_values = set(value_pattern.split("|"))

    assert fetched_values == {"toilets", "pharmacy", "atm", "shelter", "clinic", "hospital", "police"}


def test_useful_services_registry_matches_actual_fetched_tags() -> None:
    (useful_services_filter,) = coverage_import.COVERAGE_AWARE_PROFILE_FILTERS["useful_services"]
    _, value_pattern = useful_services_filter
    fetched_values = set(value_pattern.split("|"))

    assert set(IMPORT_PROFILES["useful_services"]) == fetched_values


def test_useful_services_downstream_classification_safety_unchanged() -> None:
    for tags in [
        {"amenity": "toilets"},
        {"amenity": "pharmacy"},
        {"amenity": "atm"},
        {"amenity": "shelter"},
        {"amenity": "clinic"},
        {"amenity": "hospital"},
        {"amenity": "police"},
    ]:
        result = classify_osm_place(tags, profile="useful_services")
        assert result.tourist_eligible is False
        assert result.is_route_eligible is False
