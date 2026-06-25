from collections import Counter

from services.coverage_gap_service import CRITICAL_POLICIES, MATCHED_STATUSES, load_known_poi_seed


def test_kutaisi_known_poi_seed_contains_user_reported_items() -> None:
    items = [item for item in load_known_poi_seed() if item["city_slug"] == "kutaisi"]

    assert {item["slug"] for item in items} == {
        "bagrati-cathedral",
        "motsameta-monastery",
        "gelati-monastery",
        "sanapiro",
        "kebaby-bikentiya",
        "kutaisi-amusement-park",
        "sataplia-cave",
    }


def test_known_poi_seed_has_required_quality_fields() -> None:
    for item in load_known_poi_seed():
        assert item["city_slug"]
        assert item["slug"]
        assert item["name_en"] or item.get("name_ru") or item.get("name_local")
        assert isinstance(item["lat"], float)
        assert isinstance(item["lng"], float)
        assert item["expected_category"]
        assert item["expected_scope"]
        assert item["expected_route_policy"]
        assert item["status"]


def test_known_poi_seed_has_actionable_readiness_counts() -> None:
    items = [item for item in load_known_poi_seed() if item["city_slug"] == "kutaisi"]
    statuses = Counter(item.get("status") or "missing" for item in items)
    critical_unresolved = sum(
        1 for item in items
        if item.get("expected_route_policy") in CRITICAL_POLICIES
        and item.get("status") not in MATCHED_STATUSES
    )

    assert len(items) == 7
    assert statuses["missing"] == 7
    assert critical_unresolved == 4
    assert {item["expected_scope"] for item in items} >= {"urban_core", "heritage_ring", "nature_daytrip"}
