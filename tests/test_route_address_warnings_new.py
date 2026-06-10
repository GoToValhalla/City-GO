from __future__ import annotations

from services.recommendation_route_serializer import serialize_final_route
from services.route_address_warnings import missing_address_warning_items
from services.route_navigation_service import navigation_payload


class _Point:
    def __init__(self, place_id: str, address: str | None, category: str = "museum"):
        self.place_id = place_id
        self.address = address
        self.category = category
        self.lat = 61.0
        self.lng = 69.0
        self.title = "Тест"
        self.visit_minutes = 30
        self.estimated_walk_minutes = 5
        self.scoring_breakdown = {}


class _Final:
    route_id = "r1"
    status = "ready"
    partial_reason = None
    total_places = 1
    total_minutes = 30
    total_estimated_minutes = 30
    estimated_distance = 1.0
    estimated_end_time = None
    has_warnings = False
    warning_count = 0
    places_with_warnings = []
    quality_score = 0.8
    quality_breakdown = {}
    total_walk_distance_meters = 100
    time_breakdown = {}
    category_distribution = {}
    warnings = []
    points = [_Point("p1", "Адрес не указан")]


def test_missing_address_route_navigation_has_map_links_new():
    payload = navigation_payload(61.0, 69.0, "Адрес не указан", category="museum")
    assert payload["has_address"] is False
    assert "открыть на карте" in str(payload["display_location"]).casefold()
    assert payload["navigation_url_google"]
    assert payload["navigation_url_yandex"]
    assert payload["navigation_url_osm"]


def test_missing_address_route_adds_warning_new():
    warnings = missing_address_warning_items(_Final.points)
    assert warnings
    assert warnings[0]["type"] == "missing_address"
    assert warnings[0]["affected_place_ids"] == ["p1"]

    payload = serialize_final_route(_Final())
    assert any(item["type"] == "missing_address" for item in payload["user_warnings"])
