from __future__ import annotations

import pytest

from services.route_builder_v2_service import (
    CATEGORY_BUILDER,
    MANUAL_BUILDER,
    QUICK_BUILD,
    SLOT_BUILDER,
    RouteBuilderV2Error,
    RouteBuilderV2Request,
    assert_route_builder_v2_mode_supported,
    build_route_builder_v2_plan,
    normalize_route_builder_request,
)
from tests.allure_support import title


@title("Route Builder v2 поддерживает четыре режима")
def test_route_builder_v2_supports_four_modes() -> None:
    assert_route_builder_v2_mode_supported(QUICK_BUILD)
    assert_route_builder_v2_mode_supported(CATEGORY_BUILDER)
    assert_route_builder_v2_mode_supported(MANUAL_BUILDER)
    assert_route_builder_v2_mode_supported(SLOT_BUILDER)
    assert_route_builder_v2_mode_supported("auto")
    assert_route_builder_v2_mode_supported("quick_build")

    with pytest.raises(RouteBuilderV2Error):
        assert_route_builder_v2_mode_supported("legacy_magic")


@title("Route Builder v2 normalizes request city and lists")
def test_route_builder_v2_normalizes_request_city_and_lists() -> None:
    request = normalize_route_builder_request(
        {
            "mode": "category_build",
            "city_id": "10",
            "profile": "Overview",
            "categories": ["Museum", "museum", "park"],
            "selected_place_ids": ["1", 1, 2, 0, -5],
            "duration_minutes": "120",
        }
    )

    assert request.mode == CATEGORY_BUILDER
    assert request.city_id == 10
    assert request.profile == "overview"
    assert request.categories == ("museum", "park")
    assert request.selected_place_ids == (1, 2)
    assert request.duration_minutes == 120

    with pytest.raises(RouteBuilderV2Error):
        normalize_route_builder_request({"mode": QUICK_BUILD})

    with pytest.raises(RouteBuilderV2Error):
        normalize_route_builder_request({"mode": QUICK_BUILD, "city_slug": "almaty", "duration_minutes": 0})


@title("Quick Build creates instant executor plan and ignores extra mode data")
def test_quick_build_creates_instant_executor_plan() -> None:
    plan = build_route_builder_v2_plan(
        {
            "mode": "auto",
            "city_slug": "almaty",
            "categories": ["museum"],
            "selected_place_ids": [1, 2],
            "duration_minutes": 180,
        }
    )

    assert plan.mode == QUICK_BUILD
    assert plan.executor_mode == "instant"
    assert plan.expected_min_points == 3
    assert plan.duration_minutes == 180
    assert plan.warnings == ("quick_ignores_categories", "quick_ignores_manual_selection")


@title("Category Builder requires categories and keeps unique order")
def test_category_builder_requires_categories_and_keeps_unique_order() -> None:
    plan = build_route_builder_v2_plan(
        {
            "mode": CATEGORY_BUILDER,
            "city_slug": "almaty",
            "categories": ["museum", "park", "museum"],
        }
    )

    assert plan.mode == CATEGORY_BUILDER
    assert plan.categories == ("museum", "park")
    assert plan.expected_min_points == 2

    with pytest.raises(RouteBuilderV2Error):
        build_route_builder_v2_plan({"mode": CATEGORY_BUILDER, "city_slug": "almaty"})


@title("Manual Builder preserves selected point order and removes duplicates")
def test_manual_builder_preserves_selected_point_order_and_removes_duplicates() -> None:
    plan = build_route_builder_v2_plan(
        {
            "mode": MANUAL_BUILDER,
            "city_id": 10,
            "selected_place_ids": [5, 3, 5, 8],
        }
    )

    assert plan.mode == MANUAL_BUILDER
    assert plan.selected_place_ids == (5, 3, 8)
    assert plan.expected_min_points == 3
    assert plan.expected_max_points == 3

    with pytest.raises(RouteBuilderV2Error):
        build_route_builder_v2_plan({"mode": MANUAL_BUILDER, "city_id": 10, "selected_place_ids": [5]})


@title("Slot Builder validates slots and computes point bounds")
def test_slot_builder_validates_slots_and_computes_point_bounds() -> None:
    plan = build_route_builder_v2_plan(
        RouteBuilderV2Request(
            mode=SLOT_BUILDER,
            city_slug="almaty",
            slots=(
                {"type": "anchor", "min_count": 1, "max_count": 2},
                {"category": "coffee", "min_count": 1},
            ),
        )
    )

    assert plan.mode == SLOT_BUILDER
    assert plan.expected_min_points == 2
    assert plan.expected_max_points == 3
    assert plan.slots == (
        {"type": "anchor", "min_count": 1, "max_count": 2, "required": True},
        {"type": "coffee", "min_count": 1, "max_count": 1, "required": True},
    )

    with pytest.raises(RouteBuilderV2Error):
        build_route_builder_v2_plan({"mode": SLOT_BUILDER, "city_slug": "almaty"})

    with pytest.raises(RouteBuilderV2Error):
        build_route_builder_v2_plan({"mode": SLOT_BUILDER, "city_slug": "almaty", "slots": [{"min_count": 1}]})

    with pytest.raises(RouteBuilderV2Error):
        build_route_builder_v2_plan(
            {
                "mode": SLOT_BUILDER,
                "city_slug": "almaty",
                "slots": [{"type": "place", "min_count": 13, "max_count": 13}],
            }
        )
