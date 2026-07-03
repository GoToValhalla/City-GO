from __future__ import annotations

import json
from types import SimpleNamespace

from scripts.production_smoke import validate_route_response
from services.place_coverage_route_score import route_features
from services.route_diversity_policy import (
    add_category,
    can_use_category,
    is_route_junk_category,
    normalize_category,
)
from services.route_finalize_metrics import compute_distance
from services.route_quality_score import build_route_quality_score, minimum_points_for_budget
from services.route_user_warnings import route_warning_message, user_warnings
from tests.allure_support import title


@title("Route distance summary uses kilometer scale, not raw coordinate delta")
def test_route_distance_summary_uses_kilometer_scale() -> None:
    ctx = SimpleNamespace(location=(40.1792, 44.4991))
    route = [SimpleNamespace(lat=40.1850, lng=44.5100)]

    distance = compute_distance(route, ctx)  # type: ignore[arg-type]

    assert distance > 0.9
    assert distance < 2.0


@title("Route warning codes are mapped to user-facing text")
def test_route_warning_codes_are_mapped_to_user_facing_text() -> None:
    final = SimpleNamespace(warnings=["route_built_without_selected_interests", "neutral_poi_added"], places_with_warnings=[])

    warnings = user_warnings(final)

    assert all("_" not in str(item["user_message"]) for item in warnings)
    assert route_warning_message("route_budget_overflow_tolerated") == "Маршрут немного выходит за выбранное время."


@title("Inland cities do not get sea route feature from generic text")
def test_inland_cities_do_not_get_sea_route_feature_from_generic_text() -> None:
    places = [
        SimpleNamespace(category="promenade", title="River walk", short_description="Central walking place"),
        SimpleNamespace(category="museum", title="City museum", short_description="Culture"),
    ]

    assert route_features(places) == []  # type: ignore[arg-type]


@title("Explicit beach category enables sea route feature")
def test_explicit_beach_category_enables_sea_route_feature() -> None:
    places = [SimpleNamespace(category="beach", title="Beach", short_description="")]

    assert route_features(places) == ["sea"]  # type: ignore[arg-type]


@title("Route quality marks two point long routes as weak")
def test_route_quality_marks_two_point_long_routes_as_weak() -> None:
    assert minimum_points_for_budget(74) == 1
    assert minimum_points_for_budget(75) == 2
    assert minimum_points_for_budget(120) == 2
    assert minimum_points_for_budget(149) == 2

    route = [_quality_point("museum"), _quality_point("park")]

    quality = build_route_quality_score(route, expected_stops=4, budget_minutes=120, warnings=[])

    assert quality.minimum_points == 2
    assert quality.actual_points == 2
    assert quality.status == "weak"


@title("Route diversity normalizes aliases and blocks service junk")
def test_route_diversity_normalizes_aliases_and_blocks_service_junk() -> None:
    assert normalize_category("coffee") == "cafe"
    assert normalize_category("attraction") == "landmark"
    assert normalize_category("promenade") == "walk"
    assert is_route_junk_category("pharmacy") is True
    assert is_route_junk_category("bus_stop") is True
    assert can_use_category("bank", {}) is False


@title("Route diversity caps food family for overview walks")
def test_route_diversity_caps_food_family_for_overview_walks() -> None:
    used = add_category("cafe", {})
    used = add_category("restaurant", used)

    assert can_use_category("food", used) is False
    assert can_use_category("museum", used) is True


@title("Production route smoke allows honest weak route but blocks junk")
def test_production_route_smoke_allows_honest_weak_route_but_blocks_junk() -> None:
    weak_payload = {
        "status": "partial_route",
        "quality_status": "weak",
        "partial_reason": "Маршрут короткий: в городе мало готовых данных.",
        "total_places": 2,
        "points": [_route_payload_point("1", "Museum", "museum"), _route_payload_point("2", "Park", "park")],
        "user_warnings": [{"user_message": "Маршрут короткий: в городе мало готовых данных."}],
    }
    junk_payload = {
        "status": "ready",
        "quality_status": "good",
        "total_places": 3,
        "points": [
            _route_payload_point("1", "Museum", "museum"),
            _route_payload_point("2", "Аптека 24", "pharmacy"),
            _route_payload_point("3", "Park", "park"),
        ],
    }

    assert validate_route_response(json.dumps(weak_payload), 200).status == "ok"
    assert validate_route_response(json.dumps(junk_payload), 200).failed is True


@title("Production route smoke fails raw technical user-facing warning codes")
def test_production_route_smoke_fails_raw_technical_user_facing_warning_codes() -> None:
    payload = {
        "status": "ready",
        "quality_status": "good",
        "total_places": 3,
        "points": [
            _route_payload_point("1", "Museum", "museum"),
            _route_payload_point("2", "Park", "park"),
            _route_payload_point("3", "View", "viewpoint"),
        ],
        "user_warnings": [{"user_message": "route_short_due_to_low_place_density"}],
    }

    result = validate_route_response(json.dumps(payload), 200)

    assert result.failed is True
    assert result.detail == "raw_technical_code_at_user_warnings[0].user_message"


def _quality_point(category: str) -> SimpleNamespace:
    return SimpleNamespace(
        category=category,
        lat=40.1,
        lng=44.5,
        visit_minutes=25,
        estimated_walk_minutes=5,
        address="Center",
        image_url="https://example.test/photo.jpg",
        short_description="Good place",
        validation={"is_valid": True},
    )


def _route_payload_point(place_id: str, title: str, category: str) -> dict[str, object]:
    return {"place_id": place_id, "title": title, "category": category, "lat": 40.1, "lng": 44.5}
