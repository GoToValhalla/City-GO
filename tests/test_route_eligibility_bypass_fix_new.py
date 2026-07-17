"""Regression coverage for the route-eligibility catalog-only visibility
bypass fix: a Place that is publicly catalog-visible (is_active,
is_published, is_visible_in_catalog all True) but explicitly marked
is_route_eligible=False must never be selectable through any route
edit/build entrypoint. Before the fix, services/user_route_edit_service.py,
services/user_route_place_loader.py, services/user_route_slot_build_service.py,
and services/user_route_replacement_loader.py all used
apply_public_place_visibility (catalog-only, no is_route_eligible check)
instead of apply_route_eligible_filters — see
tests/test_route_catalog_visibility_bypass_ast_new.py for the static guard
that now prevents this class of bug from being reintroduced.

Every place created in this file uses is_route_eligible=False with an
otherwise fully public, catalog-visible place (category="museum" — inside
ALLOWED_ROUTE_CATEGORIES, so the bypass would previously have let it
through purely because of the missing column check).
"""

from __future__ import annotations

from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteIntent,
    UserRoutePoint,
    UserRouteReplacePlaceRequest,
    UserRouteSlotRequest,
    UserRouteState,
    UserRouteStructuredBuildRequest,
    UserRouteUpdateRequest,
)
from services.user_route_edit_service import UserRouteEditService
from services.user_route_place_loader import load_ordered_places, load_place
from services.user_route_replacement_loader import find_replacement_place
from services.user_route_slot_build_service import UserRouteSlotBuildService


def _point(place, position: int) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=str(place.id),
        city_slug="route-eligibility-city",
        position=position,
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        lat=float(place.lat),
        lng=float(place.lng),
        category=str(place.category or "museum"),
        visit_minutes=20,
    )


def _intent() -> UserRouteIntent:
    return UserRouteIntent(lat=54.9600, lng=20.4700, city_id="route-eligibility-city", time_budget_minutes=180)


def _current_route(points: list[UserRoutePoint]) -> UserRouteState:
    return UserRouteState(
        route_id="route-eligibility-test",
        revision=1,
        status="ready",
        context=_intent(),
        total_places=len(points),
        total_minutes=len(points) * 20,
        total_estimated_minutes=len(points) * 20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=points,
    )


def test_load_place_rejects_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    ineligible = place_factory(
        city_id=city.id, slug="ineligible-1", title="Ineligible", category="museum",
        lat=54.9600, lng=20.4700, is_route_eligible=False,
    )
    assert load_place(db_session, str(ineligible.id)) is None


def test_load_ordered_places_drops_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="eligible-1", title="Eligible", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(
        city_id=city.id, slug="ineligible-2", title="Ineligible", category="park",
        lat=54.9650, lng=20.4750, is_route_eligible=False,
    )
    route = _current_route([_point(eligible, 1), _point(ineligible, 2)])
    places = load_ordered_places(db_session, route)
    assert [p.id for p in places] == [eligible.id]


def test_add_place_rejects_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    first = place_factory(city_id=city.id, slug="first", title="First", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(
        city_id=city.id, slug="ineligible-3", title="Ineligible", category="park",
        lat=54.9650, lng=20.4750, is_route_eligible=False,
    )
    current_route = _current_route([_point(first, 1)])

    result = UserRouteEditService().add_place(
        db_session,
        UserRouteAddPlaceRequest(current_route=current_route, place_id=str(ineligible.id), insert_after_place_id=None),
    )

    assert [point.place_id for point in result.points] == [str(first.id)]
    assert any("не найдено" in warning.lower() or "не опубликовано" in warning.lower() for warning in result.warnings)


def test_replace_place_rejects_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    first = place_factory(city_id=city.id, slug="first-r", title="First", category="museum", lat=54.9600, lng=20.4700)
    second = place_factory(city_id=city.id, slug="second-r", title="Second", category="park", lat=54.9650, lng=20.4750)
    ineligible = place_factory(
        city_id=city.id, slug="ineligible-4", title="Ineligible", category="culture",
        lat=54.9700, lng=20.4800, is_route_eligible=False,
    )
    current_route = _current_route([_point(first, 1), _point(second, 2)])

    result = UserRouteEditService().replace_place(
        db_session,
        UserRouteReplacePlaceRequest(current_route=current_route, old_place_id=str(second.id), new_place_id=str(ineligible.id)),
    )

    # The ineligible replacement must not appear anywhere in the resulting route.
    assert str(ineligible.id) not in [point.place_id for point in result.points]


def test_alternatives_excludes_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    current = place_factory(city_id=city.id, slug="alt-current", title="Current", category="museum", lat=54.9600, lng=20.4700)
    eligible = place_factory(city_id=city.id, slug="alt-eligible", title="Alt Eligible", category="museum", lat=54.9605, lng=20.4705)
    ineligible = place_factory(
        city_id=city.id, slug="alt-ineligible", title="Alt Ineligible", category="museum",
        lat=54.9603, lng=20.4703, is_route_eligible=False,
    )
    route = _current_route([_point(current, 1)])

    result = UserRouteEditService().alternatives(db_session, route, str(current.id), limit=5)

    option_ids = {option.place_id for option in result.options}
    assert str(eligible.id) in option_ids
    assert str(ineligible.id) not in option_ids


def test_structured_options_excludes_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="struct-eligible", title="Struct Eligible", category="museum", lat=54.9600, lng=20.4700)
    place_factory(
        city_id=city.id, slug="struct-ineligible", title="Struct Ineligible", category="museum",
        lat=54.9602, lng=20.4702, is_route_eligible=False,
    )
    request = UserRouteStructuredBuildRequest(
        lat=54.9600, lng=20.4700, city_id="route-eligibility-city",
        slots=[UserRouteSlotRequest(slot_id="slot-1", category="museum")],
    )

    result = UserRouteEditService().structured_options(db_session, request)

    option_ids = {option.place_id for slot in result.slots for option in slot.options}
    assert str(eligible.id) in option_ids
    assert len(result.slots[0].options) == 1


def test_update_order_drops_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="reorder-eligible", title="Reorder Eligible", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(
        city_id=city.id, slug="reorder-ineligible", title="Reorder Ineligible", category="park",
        lat=54.9650, lng=20.4750, is_route_eligible=False,
    )
    current_route = _current_route([_point(eligible, 1), _point(ineligible, 2)])

    result = UserRouteEditService().update_order(
        db_session,
        UserRouteUpdateRequest(current_route=current_route, ordered_place_ids=[str(ineligible.id), str(eligible.id)]),
    )

    assert [point.place_id for point in result.points] == [str(eligible.id)]


def test_slot_build_selected_place_rejects_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    ineligible = place_factory(
        city_id=city.id, slug="slot-selected-ineligible", title="Slot Ineligible", category="museum",
        lat=54.9600, lng=20.4700, is_route_eligible=False,
    )
    service = UserRouteSlotBuildService()
    place = service._selected_place(db_session, ineligible.id, "museum", set())
    assert place is None


def test_slot_build_first_candidate_skips_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    from schemas.user_route import UserRouteBuildRequest

    city = city_factory(slug="route-eligibility-city")
    place_factory(
        city_id=city.id, slug="slot-candidate-ineligible", title="Slot Candidate Ineligible", category="museum",
        lat=54.9600, lng=20.4700, is_route_eligible=False,
    )
    eligible = place_factory(city_id=city.id, slug="slot-candidate-eligible", title="Slot Candidate Eligible", category="museum", lat=54.9601, lng=20.4701)

    service = UserRouteSlotBuildService()
    request = UserRouteBuildRequest(lat=54.9600, lng=20.4700, city_id=city.slug)
    place = service._first_slot_candidate(db_session, request, "museum", set())
    assert place is not None
    assert place.id == eligible.id


def test_find_replacement_place_excludes_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="replacement-eligible", title="Replacement Eligible", category="cafe", lat=54.9605, lng=20.4705)
    place_factory(
        city_id=city.id, slug="replacement-ineligible", title="Replacement Ineligible", category="cafe",
        lat=54.9601, lng=20.4701, is_route_eligible=False,
    )
    # route.context.city_id is a slug string on the schema, while
    # find_replacement_place filters Place.city_id (an integer FK) when
    # present — matching the existing test pattern (test_user_route_
    # correct_service.py), city_id is left unset here so the loader falls
    # back to its unfiltered-by-city candidate pool, same as production
    # callers that omit it.
    route = _current_route([]).model_copy(update={"context": UserRouteIntent(lat=54.9600, lng=20.4700, time_budget_minutes=180)})
    replacement = find_replacement_place(db_session, route=route, category="cafe", excluded_ids=set())
    assert replacement is not None
    assert replacement.id == eligible.id
