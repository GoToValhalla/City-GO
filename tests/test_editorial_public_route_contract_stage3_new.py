"""Stage 3 DEFECT 1: editorial public routes enforce full city/place contract."""

from __future__ import annotations

from models.route import Route
from models.route_place import RoutePlace
from services.route_place_service import get_route_places_by_route_id
from services.route_service import (
    build_route_points,
    get_public_route_by_id,
    get_public_route_by_slug,
    get_public_routes_by_city_slug,
    get_route_by_id,
)


def _route(db, city, *, slug: str, is_active: bool = True) -> Route:
    route = Route(city_id=city.id, slug=slug, title=slug, is_active=is_active)
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


def _points(db, route, places) -> None:
    for index, place in enumerate(places, start=1):
        db.add(RoutePlace(route_id=route.id, place_id=place.id, position=index))
    db.commit()
    db.refresh(route)


def test_editorial_active_route_published_city_visible_new(client, db_session, city_factory, published_place_factory):
    city = city_factory(slug="ed-ok-city", launch_status="published")
    places = [
        published_place_factory(slug="ed-ok-1", city_id=city.id, category="cafe"),
        published_place_factory(slug="ed-ok-2", city_id=city.id, category="park"),
    ]
    route = _route(db_session, city, slug="ed-ok-route")
    _points(db_session, route, places)

    listed = client.get("/routes/", params={"city_slug": city.slug})
    by_id = client.get(f"/routes/{route.id}")
    by_slug = client.get(f"/routes/by-slug/{route.slug}")
    places_resp = client.get("/route-places/", params={"route_id": route.id})

    assert listed.status_code == 200 and [row["id"] for row in listed.json()] == [route.id]
    assert by_id.status_code == 200 and len(by_id.json()["points"]) == 2
    assert by_slug.status_code == 200 and len(by_slug.json()["points"]) == 2
    assert places_resp.status_code == 200 and len(places_resp.json()) == 2


def test_editorial_inactive_route_hidden_new(client, db_session, city_factory, published_place_factory):
    city = city_factory(slug="ed-inactive-city")
    places = [
        published_place_factory(slug="ed-in-1", city_id=city.id, category="cafe"),
        published_place_factory(slug="ed-in-2", city_id=city.id, category="park"),
    ]
    route = _route(db_session, city, slug="ed-inactive", is_active=False)
    _points(db_session, route, places)

    assert client.get(f"/routes/{route.id}").status_code == 404
    assert get_public_route_by_slug(db_session, route.slug) is None
    assert get_route_by_id(db_session, route.id) is not None


def test_editorial_route_in_unpublished_city_hidden_new(client, db_session, city_factory, published_place_factory):
    for launch_status in ("preview", "preparing"):
        city = city_factory(slug=f"ed-city-{launch_status}", launch_status=launch_status)
        places = [
            published_place_factory(slug=f"ed-{launch_status}-1", city_id=city.id, category="cafe"),
            published_place_factory(slug=f"ed-{launch_status}-2", city_id=city.id, category="park"),
        ]
        route = _route(db_session, city, slug=f"ed-route-{launch_status}")
        _points(db_session, route, places)
        assert client.get(f"/routes/{route.id}").status_code == 404
        assert get_public_routes_by_city_slug(db_session, city.slug) == []


def test_editorial_ineligible_point_not_exposed_fail_closed_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    city = city_factory(slug="ed-stale-city")
    good = [
        published_place_factory(slug="ed-good-1", city_id=city.id, category="cafe"),
        published_place_factory(slug="ed-good-2", city_id=city.id, category="park"),
    ]
    bad = place_factory(
        slug="ed-bad-bank",
        city_id=city.id,
        category="bank",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=False,
        publication_status="published",
    )
    route = _route(db_session, city, slug="ed-mixed")
    _points(db_session, route, [*good, bad])

    detail = client.get(f"/routes/{route.id}")
    assert detail.status_code == 200
    place_ids = {row["place_id"] for row in detail.json()["points"]}
    assert bad.id not in place_ids
    assert place_ids == {good[0].id, good[1].id}
    assert all(rp.place_id != bad.id for rp in get_route_places_by_route_id(db_session, route.id))


def test_editorial_one_valid_point_hides_entire_route_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    city = city_factory(slug="ed-one-city")
    good = published_place_factory(slug="ed-one-good", city_id=city.id, category="cafe")
    bad = place_factory(
        slug="ed-one-bad",
        city_id=city.id,
        category="pharmacy",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        publication_status="draft",
    )
    route = _route(db_session, city, slug="ed-one-point")
    _points(db_session, route, [good, bad])

    assert client.get(f"/routes/{route.id}").status_code == 404
    assert get_public_route_by_id(db_session, route.id) is None
    admin = get_route_by_id(db_session, route.id)
    assert admin is not None
    assert len(build_route_points(admin)) == 2
