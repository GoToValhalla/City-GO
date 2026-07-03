from __future__ import annotations

from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteState
from services.route_builder_v2_service import (
    CATEGORY_BUILDER,
    MANUAL_BUILDER,
    QUICK_BUILD,
    SLOT_BUILDER,
    RouteBuilderV2Error,
    apply_route_builder_v2_plan_to_intent,
    attach_route_builder_v2_result,
    build_route_builder_v2_plan,
    build_route_builder_v2_plan_from_intent,
    normalize_route_builder_request,
    route_builder_v2_output_gate,
)


def _intent(**updates: object) -> UserRouteBuildRequest:
    payload = {
        "lat": 43.238949,
        "lng": 76.889709,
        "city_id": "almaty",
        "time_budget_minutes": 180,
        "build_mode": "auto",
        "interests": [],
        "selected_place_ids": [],
        "route_slots": [],
    }
    payload.update(updates)
    return UserRouteBuildRequest(**payload)


def _point(place_id: str, title: str, category: str) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=place_id,
        city_slug="almaty",
        position=int(place_id),
        title=title,
        address="Main street 1",
        lat=43.2,
        lng=76.8,
        category=category,
        visit_minutes=20,
    )


def _state(points: list[UserRoutePoint], intent: UserRouteBuildRequest) -> UserRouteState:
    return UserRouteState(
        route_id="route-1",
        status="ready",
        context=intent,
        total_places=len(points),
        total_minutes=60,
        total_estimated_minutes=70,
        estimated_distance=1.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.7,
        quality_status="acceptable",
        warnings=[],
        points=points,
        explanation={},
        debug_trace=[],
    )


def test_route_builder_v2_auto_intent_maps_to_quick_plan_new() -> None:
    plan = build_route_builder_v2_plan_from_intent(_intent(build_mode="auto", interests=["museum"]))

    assert plan.mode == QUICK_BUILD
    assert plan.executor_mode == "instant"
    assert plan.expected_min_points == 3
    assert plan.categories == ()


def test_route_builder_v2_category_intent_maps_interests_to_categories_new() -> None:
    plan = build_route_builder_v2_plan_from_intent(_intent(build_mode="by_categories", interests=["Museum", "museum", "park"]))

    assert plan.mode == CATEGORY_BUILDER
    assert plan.categories == ("museum", "park")
    assert plan.expected_min_points == 2


def test_route_builder_v2_manual_intent_preserves_selected_place_order_new() -> None:
    plan = build_route_builder_v2_plan_from_intent(_intent(build_mode="manual", selected_place_ids=["7", "3", "7", "0", "-1"]))

    assert plan.mode == MANUAL_BUILDER
    assert plan.selected_place_ids == (7, 3)
    assert plan.expected_min_points == 2
    assert plan.expected_max_points == 2


def test_route_builder_v2_constructor_intent_normalizes_slots_new() -> None:
    plan = build_route_builder_v2_plan_from_intent(
        _intent(
            build_mode="constructor",
            route_slots=[
                {"type": "Anchor", "min_count": "1", "max_count": "2"},
                {"category": "Coffee", "min_count": 1},
            ],
        )
    )

    assert plan.mode == SLOT_BUILDER
    assert plan.expected_min_points == 2
    assert plan.expected_max_points == 3
    assert plan.slots == (
        {"slot_id": "slot-1", "type": "anchor", "category": "anchor", "min_count": 1, "max_count": 2, "required": True, "duration": None, "selected_place_id": None},
        {"slot_id": "slot-2", "type": "coffee", "category": "coffee", "min_count": 1, "max_count": 1, "required": True, "duration": None, "selected_place_id": None},
    )


def test_route_builder_v2_rejects_slot_without_type_or_category_new() -> None:
    try:
        build_route_builder_v2_plan({"mode": SLOT_BUILDER, "city_slug": "almaty", "slots": [{"min_count": 1}]})
    except RouteBuilderV2Error as exc:
        assert "requires type or category" in str(exc)
    else:
        raise AssertionError("Slot without type/category must be rejected")


def test_route_builder_v2_rejects_slot_max_below_min_new() -> None:
    try:
        build_route_builder_v2_plan({"mode": SLOT_BUILDER, "city_slug": "almaty", "slots": [{"type": "coffee", "min_count": 2, "max_count": 1}]})
    except RouteBuilderV2Error as exc:
        assert "max_count must be >= min_count" in str(exc)
    else:
        raise AssertionError("Slot max_count below min_count must be rejected")


def test_route_builder_v2_rejects_slot_total_above_limit_new() -> None:
    try:
        build_route_builder_v2_plan({"mode": SLOT_BUILDER, "city_slug": "almaty", "slots": [{"type": "place", "min_count": 13, "max_count": 13}]})
    except RouteBuilderV2Error as exc:
        assert "supports up to 12 points" in str(exc)
    else:
        raise AssertionError("Slot route above max points must be rejected")


def test_route_builder_v2_output_gate_removes_pharmacy_bank_stop_and_placeholders_new() -> None:
    gate = route_builder_v2_output_gate(
        [
            _point("1", "Museum", "museum"),
            _point("2", "Аптека Горздрав", "pharmacy"),
            _point("3", "Bank", "bank"),
            _point("4", "Node 123", "park"),
            _point("5", "Central park", "park"),
        ]
    )

    assert [point.place_id for point in gate.points] == ["1", "5"]
    assert gate.removed_junk_place_ids == ("2", "3", "4")
    assert gate.warnings == ("route_builder_v2_removed_route_junk",)


def test_route_builder_v2_attach_result_keeps_public_warning_copy_and_internal_trace_new() -> None:
    intent = _intent(build_mode="auto")
    plan = build_route_builder_v2_plan_from_intent(intent)
    state = _state([_point("1", "Central park", "park")], intent)

    result = attach_route_builder_v2_result(state, plan)

    assert result.status == "partial_route"
    assert result.partial_reason == "route_builder_v2_insufficient_points"
    assert result.warnings == ["После проверки осталось мало подходящих точек."]
    assert result.explanation["warnings"] == ["После проверки осталось мало подходящих точек."]
    assert result.explanation["route_builder_v2"]["mode"] == "Быстрый маршрут"
    assert "data_contract" not in result.explanation["route_builder_v2"]
    assert result.debug_trace[0]["data_contract"] == "public_catalog_visible_route_eligible_only"


def test_route_builder_v2_apply_category_plan_merges_interests_without_duplicates_new() -> None:
    intent = _intent(build_mode="by_categories", interests=["museum"])
    plan = build_route_builder_v2_plan({"mode": CATEGORY_BUILDER, "city_slug": "almaty", "categories": ["museum", "park"]})

    updated = apply_route_builder_v2_plan_to_intent(intent, plan)

    assert updated.interests == ["museum", "park"]


def test_route_builder_v2_normalize_request_requires_city_scope_new() -> None:
    try:
        normalize_route_builder_request({"mode": QUICK_BUILD})
    except RouteBuilderV2Error as exc:
        assert "requires city_id or city_slug" in str(exc)
    else:
        raise AssertionError("Route Builder v2 request without city scope must be rejected")
