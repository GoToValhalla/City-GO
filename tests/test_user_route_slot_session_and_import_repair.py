from __future__ import annotations

import models.route_session  # noqa: F401
from models.city_admin_import_job import CityAdminImportJob
from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteSessionActionRequest, UserRouteSessionStartRequest, UserRouteState
from services.admin_city_import_job_service import _run_auto_repair
from services.user_route_session_service import UserRouteSessionService
from services.user_route_slot_build_service import UserRouteSlotBuildService
from tests.allure_support import title


@title("Slot constructor fills route in requested slot order")
def test_slot_constructor_fills_route_in_requested_slot_order(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="yerevan", name="Yerevan")
    cafe = published_place_factory(city_id=city.id, title="Morning cafe", category="cafe", lat=40.18, lng=44.50, address="Cafe street", image_url="https://img/cafe.jpg")
    museum = published_place_factory(city_id=city.id, title="City museum", category="museum", lat=40.19, lng=44.51, address="Museum street", image_url="https://img/museum.jpg")

    request = UserRouteBuildRequest(
        lat=40.1792,
        lng=44.4991,
        city_id="yerevan",
        build_mode="constructor",
        time_budget_minutes=120,
        interests=[],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=None,
        user_id="test-user",
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True, "selected_place_id": str(cafe.id)},
            {"slot_id": "museum", "category": "museum", "required": True, "selected_place_id": str(museum.id)},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert [point.place_id for point in route.points] == [str(cafe.id), str(museum.id)]
    assert route.explanation["slot_matches"][0]["slot_id"] == "coffee"
    assert route.status == "ready"


@title("Slot constructor returns honest partial when required slot is missing")
def test_slot_constructor_returns_partial_when_required_slot_missing(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="yerevan-partial", name="Yerevan Partial")
    published_place_factory(city_id=city.id, title="Only cafe", category="cafe", lat=40.18, lng=44.50, address="Cafe street")

    request = UserRouteBuildRequest(
        lat=40.1792,
        lng=44.4991,
        city_id="yerevan-partial",
        build_mode="constructor",
        time_budget_minutes=120,
        interests=[],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=None,
        user_id="test-user",
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True},
            {"slot_id": "view", "category": "viewpoint", "required": True},
        ],
    )

    route = UserRouteSlotBuildService().build(db_session, request)

    assert route.status == "partial_route"
    assert route.partial_reason == "slot_constructor_missing_required_slot"
    assert route.explanation["slot_matches"][1]["status"] == "missing_required"


@title("Active route session persists transitions in existing route session tables")
def test_active_route_session_persists_transitions(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="session-city", name="Session City")
    first = published_place_factory(city_id=city.id, title="First", category="museum", lat=40.1, lng=44.1)
    second = published_place_factory(city_id=city.id, title="Second", category="park", lat=40.2, lng=44.2)
    route = _route_state("session-city", first.id, second.id)

    service = UserRouteSessionService()
    started = service.start(db_session, UserRouteSessionStartRequest(current_route=route, user_id="u1"))
    completed_first = service.apply_action(db_session, started.session_id, UserRouteSessionActionRequest(action="complete_point"))
    paused = service.apply_action(db_session, started.session_id, UserRouteSessionActionRequest(action="pause"))
    finished = service.apply_action(db_session, started.session_id, UserRouteSessionActionRequest(action="finish"))

    assert started.status == "active"
    assert completed_first.current_place_id == str(second.id)
    assert str(first.id) in completed_first.point_completed_at
    assert paused.status == "paused"
    assert finished.status == "completed"
    assert finished.completed_at is not None


@title("Import job auto repair hook stores summary in job details")
def test_import_job_auto_repair_hook_stores_summary(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="repair-city", name="Repair City")
    place = place_factory(city_id=city.id, category="pharmacy", address="Main")
    place.opening_hours = {"daily": "open"}
    db_session.commit()
    db_session.refresh(place)
    job = CityAdminImportJob(city_id=city.id, status="running", source="test")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    summary = _run_auto_repair(db_session, city=city, job=job, changed_place_ids=[place.id])
    db_session.commit()
    db_session.refresh(job)

    assert summary["repaired_count"] >= 1
    assert job.step_details["auto_repair"]["by_reason"]["route_ineligible_utility_or_service"] == 1


def _route_state(city_slug: str, first_id: int, second_id: int) -> UserRouteState:
    request = UserRouteBuildRequest(
        lat=40.1,
        lng=44.1,
        city_id=city_slug,
        build_mode="auto",
        time_budget_minutes=120,
        interests=[],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=None,
        user_id="u1",
    )
    return UserRouteState(
        route_id="route-session-test",
        context=request,
        total_places=2,
        total_minutes=90,
        total_estimated_minutes=100,
        estimated_distance=1.5,
        has_warnings=False,
        warning_count=0,
        quality_score=0.8,
        quality_status="good",
        points=[
            UserRoutePoint(place_id=str(first_id), city_slug=city_slug, position=1, title="First", lat=40.1, lng=44.1, category="museum", visit_minutes=30),
            UserRoutePoint(place_id=str(second_id), city_slug=city_slug, position=2, title="Second", lat=40.2, lng=44.2, category="park", visit_minutes=30),
        ],
    )
