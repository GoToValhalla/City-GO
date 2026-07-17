from __future__ import annotations

from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteBuildRequest,
    UserRouteIntent,
    UserRoutePoint,
    UserRouteReplacePlaceRequest,
    UserRouteSlotRequest,
    UserRouteState,
    UserRouteStructuredBuildRequest,
    UserRouteUpdateRequest,
)
from services.public_route_place_access import resolve_public_city_scope
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
    scope = resolve_public_city_scope(db_session, city.slug)
    assert load_place(db_session, str(ineligible.id), scope=scope) is None


def test_load_ordered_places_reconciles_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="eligible-1", title="Eligible", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(
        city_id=city.id, slug="ineligible-2", title="Ineligible", category="park",
        lat=54.9650, lng=20.4750, is_route_eligible=False,
    )
    places = load_ordered_places(db_session, _current_route([_point(eligible, 1), _point(ineligible, 2)]))
    assert [place.id for place in places] == [eligible.id]


def test_add_place_rejects_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    first = place_factory(city_id=city.id, slug="first", title="First", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(city_id=city.id, slug="ineligible-3", title="Ineligible", category="park", lat=54.9650, lng=20.4750, is_route_eligible=False)
    result = UserRouteEditService().add_place(
        db_session,
        UserRouteAddPlaceRequest(current_route=_current_route([_point(first, 1)]), place_id=str(ineligible.id)),
    )
    assert [point.place_id for point in result.points] == [str(first.id)]


def test_replace_place_rejects_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    first = place_factory(city_id=city.id, slug="first-r", title="First", category="museum", lat=54.9600, lng=20.4700)
    second = place_factory(city_id=city.id, slug="second-r", title="Second", category="park", lat=54.9650, lng=20.4750)
    ineligible = place_factory(city_id=city.id, slug="ineligible-4", title="Ineligible", category="culture", lat=54.9700, lng=20.4800, is_route_eligible=False)
    result = UserRouteEditService().replace_place(
        db_session,
        UserRouteReplacePlaceRequest(
            current_route=_current_route([_point(first, 1), _point(second, 2)]),
            old_place_id=str(second.id),
            new_place_id=str(ineligible.id),
        ),
    )
    assert [point.place_id for point in result.points] == [str(first.id), str(second.id)]


def test_alternatives_excludes_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    current = place_factory(city_id=city.id, slug="alt-current", title="Current", category="museum", lat=54.9600, lng=20.4700)
    eligible = place_factory(city_id=city.id, slug="alt-eligible", title="Alt Eligible", category="museum", lat=54.9605, lng=20.4705)
    ineligible = place_factory(city_id=city.id, slug="alt-ineligible", title="Alt Ineligible", category="museum", lat=54.9603, lng=20.4703, is_route_eligible=False)
    result = UserRouteEditService().alternatives(db_session, _current_route([_point(current, 1)]), str(current.id), limit=5)
    option_ids = {option.place_id for option in result.options}
    assert str(eligible.id) in option_ids
    assert str(ineligible.id) not in option_ids


def test_structured_options_excludes_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="struct-eligible", title="Struct Eligible", category="museum", lat=54.9600, lng=20.4700)
    place_factory(city_id=city.id, slug="struct-ineligible", title="Struct Ineligible", category="museum", lat=54.9602, lng=20.4702, is_route_eligible=False)
    request = UserRouteStructuredBuildRequest(
        lat=54.9600, lng=20.4700, city_id=city.slug,
        slots=[UserRouteSlotRequest(slot_id="slot-1", category="museum")],
    )
    result = UserRouteEditService().structured_options(db_session, request)
    option_ids = {option.place_id for slot in result.slots for option in slot.options}
    assert option_ids == {str(eligible.id)}


def test_update_order_reconciles_route_ineligible_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    eligible = place_factory(city_id=city.id, slug="reorder-eligible", title="Reorder Eligible", category="museum", lat=54.9600, lng=20.4700)
    ineligible = place_factory(city_id=city.id, slug="reorder-ineligible", title="Reorder Ineligible", category="park", lat=54.9650, lng=20.4750, is_route_eligible=False)
    result = UserRouteEditService().update_order(
        db_session,
        UserRouteUpdateRequest(
            current_route=_current_route([_point(eligible, 1), _point(ineligible, 2)]),
            ordered_place_ids=[str(ineligible.id), str(eligible.id)],
        ),
    )
    assert [point.place_id for point in result.points] == [str(eligible.id)]


def test_slot_selected_place_rejects_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    ineligible = place_factory(city_id=city.id, slug="slot-selected-ineligible", title="Slot Ineligible", category="museum", lat=54.9600, lng=20.4700, is_route_eligible=False)
    scope = resolve_public_city_scope(db_session, city.slug)
    place = UserRouteSlotBuildService()._selected_place(db_session, ineligible.id, "museum", set(), scope=scope)
    assert place is None


def test_slot_first_candidate_skips_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    place_factory(city_id=city.id, slug="slot-candidate-ineligible", title="Slot Candidate Ineligible", category="museum", lat=54.9600, lng=20.4700, is_route_eligible=False)
    eligible = place_factory(city_id=city.id, slug="slot-candidate-eligible", title="Slot Candidate Eligible", category="museum", lat=54.9601, lng=20.4701)
    request = UserRouteBuildRequest(lat=54.9600, lng=20.4700, city_id=city.slug)
    place = UserRouteSlotBuildService()._first_slot_candidate(db_session, request, "museum", set())
    assert place is not None
    assert place.id == eligible.id


def test_replacement_excludes_route_ineligible_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-eligibility-city")
    current = place_factory(city_id=city.id, slug="replacement-current", title="Current", category="cafe", lat=54.9600, lng=20.4700)
    eligible = place_factory(city_id=city.id, slug="replacement-eligible", title="Replacement Eligible", category="cafe", lat=54.9605, lng=20.4705)
    place_factory(city_id=city.id, slug="replacement-ineligible", title="Replacement Ineligible", category="cafe", lat=54.9601, lng=20.4701, is_route_eligible=False)
    replacement = find_replacement_place(
        db_session,
        route=_current_route([_point(current, 1)]),
        category="cafe",
        excluded_ids={str(current.id)},
    )
    assert replacement is not None
    assert replacement.id == eligible.id
