from services.coverage_gap_service import build_coverage_summary, load_known_poi_seed


ALLOWED_STATUSES = {
    "missing",
    "matched",
    "needs_review",
    "source_absent",
    "out_of_scope",
    "tag_unsupported",
    "rejected_policy",
    "duplicate",
}


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
        assert item["status"] in ALLOWED_STATUSES


def test_coverage_summary_explains_scope_status_without_mutation() -> None:
    result = build_coverage_summary(None, city_slug="kutaisi")  # type: ignore[arg-type]

    assert result["total"] == 7
    assert result["summary"]["total"] == 7
    assert "by_status" in result["summary"]
    assert "by_gap_reason" in result["summary"]
    assert {item["city_slug"] for item in result["items"]} == {"kutaisi"}
