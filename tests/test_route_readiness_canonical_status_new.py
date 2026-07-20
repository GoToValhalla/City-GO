"""Regression tests for CITYGO-356.

Root cause: RouteFinalizeService/route_status() (services/route_status_service.py)
correctly computes readiness (no_route for 0 points, ready only when the
point count reaches _expected_min(expected_stops), otherwise partial_route),
but services/user_route_slot_build_service.py::UserRouteSlotBuildService.build()
unconditionally overwrote that canonical status with "ready" whenever every
required slot was filled — regardless of the actual point count. A one-point
route with its single required slot filled could therefore report "ready".

Fix: Slot Builder now only ever DOWNGRADES the canonical status (ready ->
partial_route when a required slot is missing); it never upgrades
partial_route to ready. partial_reason is set to the slot-specific reason
whenever a required slot is missing, so the gap remains correctly reported
even if the canonical status was already partial_route for an unrelated
reason (too few points).

These tests exercise both the pure canonical function
(services/route_status_service.route_status) directly and the full Slot
Builder path (real SQLite session via place_factory/city_factory), matching
the style of the existing
tests/test_user_route_slot_session_and_import_repair.py.
"""

from __future__ import annotations

from schemas.user_route import UserRouteBuildRequest
from services.route_status_service import route_status
from services.user_route_slot_build_service import UserRouteSlotBuildService


def _request(*, city_id: str, time_budget_minutes: int, route_slots: list[dict]) -> UserRouteBuildRequest:
    return UserRouteBuildRequest(
        lat=40.1792,
        lng=44.4991,
        city_id=city_id,
        build_mode="constructor",
        time_budget_minutes=time_budget_minutes,
        interests=[],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=None,
        user_id="test-user",
        route_slots=route_slots,
    )


# --- Canonical route_status() itself: no_route / one-point / two-point ----


def test_zero_points_is_no_route_new() -> None:
    assert route_status(0, 4) == "no_route"


def test_one_point_is_never_ready_new() -> None:
    """Regardless of expected_stops, _expected_min() is always >= 2, so a
    single point can never be canonically "ready"."""
    for expected_stops in (1, 2, 3, 4, 6, 8, 20):
        assert route_status(1, expected_stops) == "partial_route", expected_stops


def test_two_points_ready_only_if_canonical_status_allows_new() -> None:
    # expected_stops=2 -> _expected_min=2 -> 2 points is enough.
    assert route_status(2, 2) == "ready"
    # expected_stops=4 -> _expected_min=3 -> 2 points is NOT enough.
    assert route_status(2, 4) == "partial_route"


def test_no_new_status_values_introduced_new() -> None:
    seen = {route_status(n, expected) for n in range(0, 9) for expected in (1, 2, 3, 4, 6, 8)}
    assert seen <= {"no_route", "partial_route", "ready"}


# --- Slot Builder must never overwrite canonical partial_route with ready -


def test_slot_builder_one_point_never_reports_ready_new(db_session, city_factory, published_place_factory) -> None:
    """The exact CITYGO-356 regression: a single required slot, filled, used
    to force status="ready" via the old unconditional overwrite."""
    city = city_factory(slug="one-point-city")
    cafe = published_place_factory(city_id=city.id, title="Only cafe", category="cafe", lat=40.18, lng=44.50)

    request = _request(
        city_id="one-point-city",
        time_budget_minutes=60,
        route_slots=[{"slot_id": "coffee", "category": "cafe", "required": True, "selected_place_id": str(cafe.id)}],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert len(route.points) == 1
    assert route.status != "ready"
    assert route.status == "partial_route"


def test_slot_builder_two_points_matches_canonical_ready_new(db_session, city_factory, published_place_factory) -> None:
    """budget=60 -> expected_min=2 -> 2 filled required slots -> canonical
    ready, and Slot Builder must not downgrade a canonically-ready route
    just because slots happen to be involved."""
    city = city_factory(slug="two-point-ready-city")
    cafe = published_place_factory(city_id=city.id, title="Cafe", category="cafe", lat=40.18, lng=44.50)
    museum = published_place_factory(city_id=city.id, title="Museum", category="museum", lat=40.19, lng=44.51)

    request = _request(
        city_id="two-point-ready-city",
        time_budget_minutes=60,
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True, "selected_place_id": str(cafe.id)},
            {"slot_id": "museum", "category": "museum", "required": True, "selected_place_id": str(museum.id)},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert len(route.points) == 2
    assert route.status == "ready"


def test_slot_builder_two_points_matches_canonical_partial_when_budget_needs_more_new(
    db_session, city_factory, published_place_factory
) -> None:
    """budget=120 -> expected_min=3 -> 2 filled required slots is NOT enough
    for canonical readiness, even though every required slot is filled.
    Before the fix, Slot Builder would force "ready" here regardless."""
    city = city_factory(slug="two-point-partial-city")
    cafe = published_place_factory(city_id=city.id, title="Cafe", category="cafe", lat=40.18, lng=44.50)
    museum = published_place_factory(city_id=city.id, title="Museum", category="museum", lat=40.19, lng=44.51)

    request = _request(
        city_id="two-point-partial-city",
        time_budget_minutes=120,
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True, "selected_place_id": str(cafe.id)},
            {"slot_id": "museum", "category": "museum", "required": True, "selected_place_id": str(museum.id)},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert len(route.points) == 2
    assert route.status == "partial_route"


# --- Missing required vs. missing optional slot ---------------------------


def test_missing_required_slot_is_correctly_reported_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="missing-required-city")
    published_place_factory(city_id=city.id, title="Only cafe", category="cafe", lat=40.18, lng=44.50)

    request = _request(
        city_id="missing-required-city",
        time_budget_minutes=60,
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True},
            {"slot_id": "view", "category": "viewpoint", "required": True},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert route.status == "partial_route"
    assert route.partial_reason == "slot_constructor_missing_required_slot"
    missing = [m for m in route.explanation["slot_matches"] if m["status"] == "missing_required"]
    assert len(missing) == 1
    assert missing[0]["slot_id"] == "view"


def test_missing_optional_slot_does_not_force_partial_new(db_session, city_factory, published_place_factory) -> None:
    """An unfilled OPTIONAL slot must not, by itself, downgrade a
    canonically-ready route to partial_route — only missing REQUIRED slots
    may affect status."""
    city = city_factory(slug="missing-optional-city")
    cafe = published_place_factory(city_id=city.id, title="Cafe", category="cafe", lat=40.18, lng=44.50)
    museum = published_place_factory(city_id=city.id, title="Museum", category="museum", lat=40.19, lng=44.51)

    request = _request(
        city_id="missing-optional-city",
        time_budget_minutes=60,
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True, "selected_place_id": str(cafe.id)},
            {"slot_id": "museum", "category": "museum", "required": True, "selected_place_id": str(museum.id)},
            {"slot_id": "bonus", "category": "bar", "required": False},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert len(route.points) == 2
    assert route.status == "ready"
    assert route.partial_reason is None
    missing = [m for m in route.explanation["slot_matches"] if m["status"] == "missing_optional"]
    assert len(missing) == 1
    assert missing[0]["slot_id"] == "bonus"


def test_zero_points_from_slot_builder_is_no_route_new(db_session, city_factory) -> None:
    city_factory(slug="empty-city")

    request = _request(
        city_id="empty-city",
        time_budget_minutes=60,
        route_slots=[{"slot_id": "coffee", "category": "cafe", "required": True}],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert route.points == []
    assert route.status == "no_route"
