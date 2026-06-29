from types import SimpleNamespace

from services.coverage_scope_policy import resolve_scope_policy
from services.coverage_scope_suggestion_service import suggest_scopes_for_gaps
from services.osm_import_taxonomy import classify_osm_place


def test_garbage_firewall_routes_banks_and_pharmacies_to_evidence_layer() -> None:
    for tags in [
        {"amenity": "bank", "name": "Sber"},
        {"amenity": "atm", "name": "ATM"},
        {"amenity": "pharmacy", "name": "Аптека"},
        {"highway": "bus_stop", "name": "Остановка"},
    ]:
        result = classify_osm_place(tags, profile="useful_services")
        assert result.layer == "admin_evidence_only"
        assert result.tourist_eligible is False
        assert result.is_route_eligible is False


def test_service_infra_is_kept_but_not_used_as_tourist_route_target() -> None:
    result = classify_osm_place({"amenity": "toilets", "access": "yes", "name": "WC"}, profile="service_infra")

    assert result.layer == "service_layer"
    assert result.route_policy == "infra_only"
    assert result.tourist_eligible is False
    assert result.is_route_eligible is False


def test_heritage_day_trip_scope_disables_city_walking_route_eligibility() -> None:
    result = classify_osm_place(
        {"amenity": "place_of_worship", "building": "monastery", "name": "Gelati"},
        profile="heritage_religious",
        scope_type="day_trip",
        transport_required=True,
    )

    assert result.layer == "tourist_catalog"
    assert result.route_policy == "day_trip"
    assert result.tourist_eligible is True
    assert result.is_route_eligible is False
    assert result.route_exclusion_reason == "transport_required_scope"


def test_city_core_tourist_place_stays_route_eligible() -> None:
    result = classify_osm_place({"tourism": "museum", "name": "Kutaisi Museum"}, profile="tourist_core_strict", scope_type="city_core")

    assert result.layer == "tourist_catalog"
    assert result.route_policy == "city_walking"
    assert result.is_route_eligible is True


def test_scope_policy_reads_bridge_metadata_from_coverage_targets() -> None:
    scope = SimpleNamespace(
        code="gelati_motsameta",
        name="Гелати и Моцамета",
        import_profile="heritage_religious",
        coverage_targets={"scope_type": "day_trip", "transport_required": True, "max_raw_objects": 400},
    )

    policy = resolve_scope_policy(scope)

    assert policy.scope_type == "day_trip"
    assert policy.route_policy == "day_trip"
    assert policy.transport_required is True
    assert policy.max_raw_objects == 400


def test_scope_suggestion_groups_nearby_kutaisi_heritage_gaps() -> None:
    city = SimpleNamespace(slug="kutaisi")
    rows = [
        SimpleNamespace(
            id=1,
            city=city,
            lat=42.294,
            lng=42.768,
            status="out_of_scope",
            gap_reason="outside_bbox",
            expected_scope="heritage_ring",
            expected_category="culture",
            expected_route_policy="day_trip",
        ),
        SimpleNamespace(
            id=2,
            city=city,
            lat=42.282,
            lng=42.759,
            status="out_of_scope",
            gap_reason="outside_bbox",
            expected_scope="heritage_ring",
            expected_category="culture",
            expected_route_policy="day_trip",
        ),
    ]

    suggestions = suggest_scopes_for_gaps(rows)

    assert len(suggestions) == 1
    assert suggestions[0].city_slug == "kutaisi"
    assert suggestions[0].suggested_type == "heritage_day_trip"
    assert set(suggestions[0].gap_ids) == {1, 2}
