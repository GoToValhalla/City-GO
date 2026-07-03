from __future__ import annotations

import pytest
from fastapi import HTTPException

from routers.user_routes import build_user_route
from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteState
from services.route_builder_v2_service import (
    CATEGORY_BUILDER,
    QUICK_BUILD,
    attach_route_builder_v2_result,
    build_route_builder_v2_plan_from_intent,
)
from tests.allure_support import title


def _request(**updates: object) -> UserRouteBuildRequest:
    payload = {
        "lat": 43.238949,
        "lng": 76.889709,
        "start_source": "city_center",
        "build_mode": "by_categories",
        "time_budget_minutes": 180,
        "interests": ["museum", "park"],
        "avoided_categories": [],
        "excluded_place_ids": [],
        "budget_level": None,
        "pace_mode": None,
        "is_visiting": False,
        "city_id": "almaty",
        "visit_city_id": None,
        "visit_days": None,
        "user_id": None,
    }
    payload.update(updates)
    return UserRouteBuildRequest(**payload)


def _point(place_id: str, category: str, title: str) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=place_id,
        city_slug="almaty",
        position=int(place_id),
        title=title,
        address="Main street 1",
        lat=43.2 + int(place_id) / 1000,
        lng=76.8 + int(place_id) / 1000,
        category=category,
        visit_minutes=20,
    )


def _state(points: list[UserRoutePoint], request: UserRouteBuildRequest | None = None) -> UserRouteState:
    return UserRouteState(
        route_id="route-1",
        status="ready",
        context=request or _request(),
        total_places=len(points),
        total_minutes=90,
        total_estimated_minutes=100,
        estimated_distance=2.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.8,
        quality_status="good",
        category_distribution={point.category: 1 for point in points},
        warnings=[],
        points=points,
        explanation={},
        debug_trace=[],
    )


@title("Route Builder v2 derives plan from user route payload")
def test_route_builder_v2_plan_is_derived_from_user_route_payload() -> None:
    plan = build_route_builder_v2_plan_from_intent(_request())

    assert plan.mode == CATEGORY_BUILDER
    assert plan.executor_mode == "instant"
    assert plan.categories == ("museum", "park")
    assert plan.expected_min_points == 2


@title("Route Builder v2 quick mode is used for auto payload")
def test_route_builder_v2_quick_mode_from_auto_payload() -> None:
    plan = build_route_builder_v2_plan_from_intent(_request(build_mode="auto", interests=[]))

    assert plan.mode == QUICK_BUILD
    assert plan.expected_min_points == 3


@title("Route Builder v2 removes utility junk from route output")
def test_route_builder_v2_output_gate_removes_route_junk() -> None:
    request = _request()
    plan = build_route_builder_v2_plan_from_intent(request)
    state = _state(
        [
            _point("1", "museum", "City museum"),
            _point("2", "pharmacy", "Utility point"),
            _point("3", "park", "Central park"),
        ],
        request,
    )

    result = attach_route_builder_v2_result(state, plan)

    assert [point.place_id for point in result.points] == ["1", "3"]
    assert result.total_places == 2
    assert "Из маршрута убраны неподходящие сервисные точки." in result.warnings
    assert result.debug_trace[0]["stage"] == "route_builder_v2"
    assert result.debug_trace[0]["data_contract"] == "public_catalog_visible_route_eligible_only"
    assert result.explanation["route_builder_v2"]["removed_places_count"] == 1


@title("Route Builder v2 marks partial route when too few usable points remain")
def test_route_builder_v2_marks_partial_when_too_few_points_remain() -> None:
    request = _request(build_mode="auto", interests=[])
    plan = build_route_builder_v2_plan_from_intent(request)
    state = _state([_point("1", "park", "Park")], request)

    result = attach_route_builder_v2_result(state, plan)

    assert result.status == "partial_route"
    assert result.partial_reason == "route_builder_v2_insufficient_points"
    assert "После проверки осталось мало подходящих точек." in result.warnings


@title("Route Builder v2 API contract rejects invalid manual payload")
def test_route_builder_v2_api_contract_rejects_invalid_manual_payload() -> None:
    with pytest.raises(HTTPException) as exc:
        build_user_route(
            _request(build_mode="manual", selected_place_ids=["1"]),
            db=object(),  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "route_builder_v2_invalid_request"
