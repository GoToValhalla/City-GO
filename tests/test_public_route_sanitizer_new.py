from __future__ import annotations

import json

from schemas.user_route import UserRouteIntent, UserRouteState
from scripts.production_smoke import validate_route_response
from services.public_route_sanitizer import sanitize_user_route_state


def test_public_route_sanitizer_removes_nested_raw_codes_from_user_facing_fields_new() -> None:
    state = UserRouteState(
        route_id="route-raw",
        status="partial_route",
        partial_reason="route_builder_v2_insufficient_points",
        context=UserRouteIntent(lat=40.0, lng=44.0, city_id="yerevan"),
        total_places=1,
        total_minutes=60,
        total_estimated_minutes=60,
        estimated_distance=1000.0,
        has_warnings=True,
        warning_count=1,
        quality_score=0.3,
        quality_status="weak",
        warnings=["route_builder_v2_insufficient_points"],
        user_warnings=[
            {
                "type": "route_builder_v2_insufficient_points",
                "severity": "warning",
                "user_message": "route_builder_v2_insufficient_points",
                "affected_place_ids": [],
                "action_hint": "route_builder_v2_removed_route_junk",
            }
        ],
        explanation={
            "warnings": ["route_builder_v2_insufficient_points"],
            "nested": {"reason": "unknown_internal_code"},
        },
    )

    sanitized = sanitize_user_route_state(state)
    payload = sanitized.model_dump()

    assert payload["warnings"] == ["После проверки осталось мало подходящих точек."]
    assert payload["user_warnings"][0]["type"] == "route"
    assert payload["user_warnings"][0]["user_message"] == "После проверки осталось мало подходящих точек."
    assert payload["user_warnings"][0]["action_hint"] == "Из маршрута убраны неподходящие сервисные точки."
    assert payload["explanation"]["nested"]["reason"] == "Маршрут собран с ограничениями по данным."
    assert validate_route_response(json.dumps(payload, ensure_ascii=False), 200).ok
