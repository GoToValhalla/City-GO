from __future__ import annotations

from schemas.user_route import (
    UserRouteIntent,
    UserRoutePoint,
    UserRouteSlotRequest,
    UserRouteState,
    UserRouteStructuredBuildRequest,
)
from services.user_route_edit_service import UserRouteEditService
from services.user_route_place_loader import load_place


def _point(place, city_slug: str) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=str(place.id),
        city_slug=city_slug,
        position=1,
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        lat=float(place.lat),
        lng=float(place.lng),
        category=str(place.category or "museum"),
        visit_minutes=20,
    )


def _route(place, city_slug: str) -> UserRouteState:
    intent = UserRouteIntent(lat=54.96, lng=20.47, city_id=city_slug, time_budget_minutes=180)
    return UserRouteState(
        route_id="public-route-contract",
        revision=1,
        status="ready",
        context=intent,
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[_point(place, city_slug)],
    )


def test_load_place_rejects_place_from_unpublished_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-unpublished-city")
    city.launch_status = "review_required"
    db_session.commit()
    place = place_factory(
        city_id=city.id,
        slug="route-unpublished-place",
        title="Unpublished city place",
        category="museum",
        lat=54.96,
        lng=20.47,
    )

    assert load_place(db_session, str(place.id)) is None


def test_load_place_rejects_place_from_inactive_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-inactive-city")
    city.is_active = False
    db_session.commit()
    place = place_factory(
        city_id=city.id,
        slug="route-inactive-place",
        title="Inactive city place",
        category="museum",
        lat=54.96,
        lng=20.47,
    )

    assert load_place(db_session, str(place.id)) is None


def test_alternatives_stay_in_current_route_city_new(db_session, city_factory, place_factory) -> None:
    current_city = city_factory(slug="route-current-city")
    other_city = city_factory(slug="route-other-city")
    current = place_factory(
        city_id=current_city.id,
        slug="route-current-place",
        title="Current",
        category="museum",
        lat=54.96,
        lng=20.47,
    )
    same_city = place_factory(
        city_id=current_city.id,
        slug="route-same-city-alt",
        title="Same city",
        category="museum",
        lat=54.961,
        lng=20.471,
    )
    other_city_place = place_factory(
        city_id=other_city.id,
        slug="route-other-city-alt",
        title="Other city",
        category="museum",
        lat=54.9605,
        lng=20.4705,
    )

    result = UserRouteEditService().alternatives(
        db_session,
        _route(current, current_city.slug),
        str(current.id),
        limit=10,
    )

    option_ids = {option.place_id for option in result.options}
    assert str(same_city.id) in option_ids
    assert str(other_city_place.id) not in option_ids


def test_structured_options_reject_unpublished_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-structured-unpublished")
    city.launch_status = "review_required"
    db_session.commit()
    place_factory(
        city_id=city.id,
        slug="route-structured-unpublished-place",
        title="Hidden structured option",
        category="museum",
        lat=54.96,
        lng=20.47,
    )
    request = UserRouteStructuredBuildRequest(
        lat=54.96,
        lng=20.47,
        city_id=city.slug,
        slots=[UserRouteSlotRequest(slot_id="slot-1", category="museum")],
    )

    result = UserRouteEditService().structured_options(db_session, request)

    assert result.slots[0].options == []
