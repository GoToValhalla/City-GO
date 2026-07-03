from __future__ import annotations

import json

from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from scripts.production_smoke import validate_route_response
from services.route_builder_v2_service import QUICK_BUILD, RouteBuilderV2Plan, attach_route_builder_v2_result


def test_route_builder_v2_sanitizes_public_user_warning_codes_new() -> None:
    state = UserRouteState(
        route_id="route-1",
        status="ready",
        context=UserRouteIntent(lat=40.0, lng=44.0, city_id="yerevan", time_budget_minutes=120),
        total_places=1,
        total_minutes=60,
        total_estimated_minutes=60,
        estimated_distance=1000.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.5,
        quality_status="weak",
        warnings=[],
        user_warnings=[],
        points=[
            UserRoutePoint(
                place_id="1",
                position=1,
                title="Museum",
                address="Main",
                lat=40.0,
                lng=44.0,
                category="museum",
                visit_minutes=30,
            )
        ],
        explanation={},
    )
    plan = RouteBuilderV2Plan(
        mode=QUICK_BUILD,
        executor_mode="instant",
        profile="overview",
        route_policy="city_walking",
        duration_minutes=120,
        expected_min_points=3,
    )

    attached = attach_route_builder_v2_result(state, plan)
    payload = attached.model_dump()

    assert payload["warnings"] == ["После проверки осталось мало подходящих точек."]
    assert payload["user_warnings"][0]["type"] == "route"
    assert payload["user_warnings"][0]["user_message"] == "После проверки осталось мало подходящих точек."
    assert validate_route_response(json.dumps(payload, ensure_ascii=False), 200).ok
