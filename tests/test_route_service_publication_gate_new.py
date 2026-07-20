"""Regression tests for a defect discovered during CITYGO-357 inventory (not
one of the two originally reported bugs — proven here per the task's "prove
root cause with a failing regression test before fixing" rule).

Root cause: services/admin_service.py::publish_route/unpublish_route toggle
Route.is_active with explicit "publish_route"/"unpublish_route" audit-log
actions — proving is_active is the intended publication gate for the
editorial Route model (distinct from the Place-candidate route-build
pipeline covered by CITYGO-355). However services/route_service.py's
functions used by the public, unauthenticated GET /routes, GET
/routes/{id}, GET /routes/by-slug/{slug} endpoints in routers/routes.py
never filtered on Route.is_active, so an unpublished (is_active=False)
editorial route remained fully readable through the public API.

Fix: added get_public_route_by_id/get_public_route_by_slug/
get_public_routes/get_public_routes_by_city_id/get_public_routes_by_city_slug
(publication-gated) and switched routers/routes.py to them.
get_route_by_id/get_route_by_slug/get_routes* themselves are left
UNFILTERED on purpose — services/admin_service.py and
services/admin_extended_service.py (admin-only, auth-gated) reuse them to
load a route for editing, including publish_route/unpublish_route
themselves, which must be able to find an already-unpublished route to
re-publish it. Filtering those internal helpers would have broken that
admin path — this was caught and reverted before committing.

services/route_place_service.py (GET /route-places, the only caller) is
filtered directly since it has no admin caller to preserve.

services/route_session_service.py::start_route_session already correctly
gates on route.is_active (see routers/route_sessions.py) — only the plain
public read paths were missing the gate.
"""

from __future__ import annotations

from models.route import Route
from models.route_place import RoutePlace
from services.route_place_service import get_route_places, get_route_places_by_route_id
from services.route_service import (
    get_public_route_by_id,
    get_public_route_by_slug,
    get_public_routes,
    get_public_routes_by_city_id,
    get_public_routes_by_city_slug,
    get_route_by_id,
    get_route_by_slug,
    get_routes,
    get_routes_by_city_id,
    get_routes_by_city_slug,
)


def _route(db_session, city, *, slug: str, is_active: bool) -> Route:
    route = Route(city_id=city.id, slug=slug, title=f"Route {slug}", is_active=is_active)
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    return route


# --- Public (gated) variants used by routers/routes.py --------------------


def test_unpublished_route_excluded_from_public_list_by_city_slug_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-1")
    _route(db_session, city, slug="unpublished-1", is_active=False)

    assert get_public_routes_by_city_slug(db_session, "route-gate-city-1") == []


def test_unpublished_route_excluded_from_public_list_by_city_id_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-2")
    _route(db_session, city, slug="unpublished-2", is_active=False)

    assert get_public_routes_by_city_id(db_session, city.id) == []


def test_unpublished_route_excluded_from_unfiltered_public_list_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-3")
    _route(db_session, city, slug="unpublished-3", is_active=False)

    result = get_public_routes(db_session)

    assert all(route.slug != "unpublished-3" for route in result)


def test_published_route_still_returned_in_public_list_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-4")
    route = _route(db_session, city, slug="published-4", is_active=True)

    result = get_public_routes_by_city_slug(db_session, "route-gate-city-4")

    assert [r.id for r in result] == [route.id]


def test_unpublished_route_not_found_by_public_id_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-5")
    route = _route(db_session, city, slug="unpublished-5", is_active=False)

    assert get_public_route_by_id(db_session, route.id) is None


def test_unpublished_route_not_found_by_public_slug_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-6")
    _route(db_session, city, slug="unpublished-6", is_active=False)

    assert get_public_route_by_slug(db_session, "unpublished-6") is None


def test_published_route_still_found_by_public_id_and_slug_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-7")
    route = _route(db_session, city, slug="published-7", is_active=True)

    assert get_public_route_by_id(db_session, route.id) is not None
    assert get_public_route_by_slug(db_session, "published-7") is not None


# --- Internal/admin-safe variants must remain UNFILTERED -------------------


def test_internal_get_route_by_id_still_finds_unpublished_route_new(db_session, city_factory) -> None:
    """admin_service.publish_route/unpublish_route reuse get_route_by_id to
    load a route before toggling is_active — it must be able to find an
    already-unpublished route, or re-publishing would be impossible."""
    city = city_factory(slug="route-gate-city-10")
    route = _route(db_session, city, slug="unpublished-10", is_active=False)

    assert get_route_by_id(db_session, route.id) is not None


def test_internal_get_route_by_slug_still_finds_unpublished_route_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-11")
    _route(db_session, city, slug="unpublished-11", is_active=False)

    assert get_route_by_slug(db_session, "unpublished-11") is not None


def test_internal_get_routes_still_lists_unpublished_route_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-12")
    _route(db_session, city, slug="unpublished-12", is_active=False)

    result = get_routes(db_session)

    assert any(route.slug == "unpublished-12" for route in result)


def test_internal_get_routes_by_city_id_still_lists_unpublished_route_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-13")
    _route(db_session, city, slug="unpublished-13", is_active=False)

    result = get_routes_by_city_id(db_session, city.id)

    assert any(route.slug == "unpublished-13" for route in result)


def test_internal_get_routes_by_city_slug_still_lists_unpublished_route_new(db_session, city_factory) -> None:
    city = city_factory(slug="route-gate-city-14")
    _route(db_session, city, slug="unpublished-14", is_active=False)

    result = get_routes_by_city_slug(db_session, "route-gate-city-14")

    assert any(route.slug == "unpublished-14" for route in result)


# --- GET /route-places (only public caller, filtered directly) ------------


def test_unpublished_route_places_excluded_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-gate-city-8")
    route = _route(db_session, city, slug="unpublished-8", is_active=False)
    place = place_factory(city_id=city.id)
    db_session.add(RoutePlace(route_id=route.id, place_id=place.id, position=1))
    db_session.commit()

    assert get_route_places_by_route_id(db_session, route.id) == []
    assert all(rp.route_id != route.id for rp in get_route_places(db_session))


def test_published_route_places_still_returned_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-gate-city-9")
    route = _route(db_session, city, slug="published-9", is_active=True)
    place = place_factory(city_id=city.id)
    db_session.add(RoutePlace(route_id=route.id, place_id=place.id, position=1))
    db_session.commit()

    result = get_route_places_by_route_id(db_session, route.id)
    assert [rp.place_id for rp in result] == [place.id]
