from __future__ import annotations

from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteBuildRequest,
    UserRouteIntent,
    UserRoutePoint,
    UserRouteReplacePlaceRequest,
    UserRouteState,
    UserRouteUpdateRequest,
)
from services.user_route_edit_service import UserRouteEditService
from services.user_route_replacement_loader import find_replacement_place
from services.user_route_slot_build_service import UserRouteSlotBuildService


def _point(place, *, city_slug: str | None = None, position: int = 1) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=str(place.id),
        city_slug=city_slug,
        position=position,
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        lat=float(place.lat),
        lng=float(place.lng),
        category=str(place.category or "museum"),
        visit_minutes=20,
    )


def _route(place, city_slug: str) -> UserRouteState:
    return UserRouteState(
        route_id="scope-route",
        revision=1,
        status="ready",
        context=UserRouteIntent(lat=float(place.lat), lng=float(place.lng), city_id=city_slug, time_budget_minutes=180),
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[_point(place, city_slug=city_slug)],
    )


def _assert_rejected_without_state(result) -> None:
    assert result.accepted is False
    assert result.state is None
    assert result.reason


def test_add_place_rejects_other_published_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-add-a")
    other = city_factory(slug="scope-add-b")
    first = place_factory(city_id=city.id, slug="scope-add-first", category="museum", lat=54.96, lng=20.47)
    foreign = place_factory(city_id=other.id, slug="scope-add-foreign", category="park", lat=55.0, lng=21.0)

    result = UserRouteEditService().add_place(
        db_session,
        UserRouteAddPlaceRequest(current_route=_route(first, city.slug), place_id=str(foreign.id)),
    )

    _assert_rejected_without_state(result)


def test_replace_place_rejects_other_city_without_deleting_old_point_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-replace-a")
    other = city_factory(slug="scope-replace-b")
    first = place_factory(city_id=city.id, slug="scope-replace-first", category="museum", lat=54.96, lng=20.47)
    foreign = place_factory(city_id=other.id, slug="scope-replace-foreign", category="museum", lat=55.0, lng=21.0)

    result = UserRouteEditService().replace_place(
        db_session,
        UserRouteReplacePlaceRequest(
            current_route=_route(first, city.slug),
            old_place_id=str(first.id),
            new_place_id=str(foreign.id),
        ),
    )

    _assert_rejected_without_state(result)


def test_update_order_cannot_inject_other_city_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-order-a")
    other = city_factory(slug="scope-order-b")
    first = place_factory(city_id=city.id, slug="scope-order-first", category="museum", lat=54.96, lng=20.47)
    foreign = place_factory(city_id=other.id, slug="scope-order-foreign", category="museum", lat=55.0, lng=21.0)

    result = UserRouteEditService().update_order(
        db_session,
        UserRouteUpdateRequest(current_route=_route(first, city.slug), ordered_place_ids=[str(foreign.id)]),
    )

    _assert_rejected_without_state(result)


def test_slot_selected_place_is_scoped_to_requested_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-slot-a")
    other = city_factory(slug="scope-slot-b")
    local = place_factory(city_id=city.id, slug="scope-slot-local", category="museum", lat=54.96, lng=20.47)
    foreign = place_factory(city_id=other.id, slug="scope-slot-foreign", category="museum", lat=55.0, lng=21.0)
    request = UserRouteBuildRequest(
        lat=54.96,
        lng=20.47,
        city_id=city.slug,
        route_slots=[{"slot_id": "one", "category": "museum", "selected_place_id": str(foreign.id)}],
    )

    result = UserRouteSlotBuildService().build(db_session, request)

    assert [point.place_id for point in result.points] == [str(local.id)]


def test_alternatives_ignore_spoofed_point_city_slug_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-alt-a")
    other = city_factory(slug="scope-alt-b")
    current = place_factory(city_id=city.id, slug="scope-alt-current", category="museum", lat=54.96, lng=20.47)
    local = place_factory(city_id=city.id, slug="scope-alt-local", category="museum", lat=54.961, lng=20.471)
    foreign = place_factory(city_id=other.id, slug="scope-alt-foreign", category="museum", lat=54.9605, lng=20.4705)
    route = _route(current, city.slug).model_copy(update={"points": [_point(current, city_slug=other.slug)]})

    result = UserRouteEditService().alternatives(db_session, route, str(current.id), limit=10)
    option_ids = {option.place_id for option in result.options}

    assert str(local.id) in option_ids
    assert str(foreign.id) not in option_ids


def test_replacement_loader_uses_db_city_scope_not_slug_fk_comparison_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="scope-replacement-a")
    other = city_factory(slug="scope-replacement-b")
    current = place_factory(city_id=city.id, slug="scope-replacement-current", category="cafe", lat=54.96, lng=20.47)
    local = place_factory(city_id=city.id, slug="scope-replacement-local", category="cafe", lat=54.961, lng=20.471)
    place_factory(city_id=other.id, slug="scope-replacement-foreign", category="cafe", lat=54.9601, lng=20.4701)

    replacement = find_replacement_place(
        db_session,
        route=_route(current, city.slug),
        category="cafe",
        excluded_ids={str(current.id)},
    )

    assert replacement is not None
    assert replacement.id == local.id
