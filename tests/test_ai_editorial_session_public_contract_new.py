"""Package 3: AI routes use public editorial readers; sessions use canonical loader."""

from __future__ import annotations

from models.route import Route
from models.route_place import RoutePlace
from services.ai_service import process_ai_query
from services.public_editorial_route_access import (
    load_public_editorial_route_query,
    public_editorial_route_places,
)


def test_ai_routes_intent_uses_public_readers_not_admin_new(
    db_session, city_factory, published_place_factory, monkeypatch
):
    city = city_factory(slug="p3-ai-city")
    monkeypatch.setattr("services.ai_service.detect_city_slug", lambda query: city.slug)
    monkeypatch.setattr("services.ai_service.detect_city_id", lambda city_slug: city.id)
    monkeypatch.setattr("services.ai_service.detect_intent", lambda query: "routes")
    places = [
        published_place_factory(city_id=city.id, slug="p3-ai-1", category="cafe"),
        published_place_factory(city_id=city.id, slug="p3-ai-2", category="park"),
    ]
    visible = Route(city_id=city.id, slug="p3-ai-visible", title="Visible", is_active=True)
    hidden = Route(city_id=city.id, slug="p3-ai-hidden", title="Hidden", is_active=False)
    db_session.add_all([visible, hidden])
    db_session.flush()
    for index, place in enumerate(places, start=1):
        db_session.add(RoutePlace(route_id=visible.id, place_id=place.id, position=index))
    db_session.commit()

    payload = process_ai_query(query="маршруты", db=db_session)
    assert payload["intent"] == "routes"
    slugs = {row["slug"] for row in payload["results"]}
    assert "p3-ai-visible" in slugs
    assert "p3-ai-hidden" not in slugs


def test_editorial_route_session_uses_public_loader_and_city_match_new(
    client, db_session, city_factory, published_place_factory, monkeypatch
):
    monkeypatch.setattr("core.public_access_middleware.assert_web_public", lambda db: None)
    city = city_factory(slug="p3-sess-city")
    other = city_factory(slug="p3-sess-other")
    local = [
        published_place_factory(city_id=city.id, slug="p3-sess-a", category="cafe"),
        published_place_factory(city_id=city.id, slug="p3-sess-b", category="park"),
    ]
    foreign = published_place_factory(city_id=other.id, slug="p3-sess-x", category="museum")
    route = Route(city_id=city.id, slug="p3-sess-route", title="Session", is_active=True)
    db_session.add(route)
    db_session.flush()
    db_session.add_all(
        [
            RoutePlace(route_id=route.id, place_id=local[0].id, position=1),
            RoutePlace(route_id=route.id, place_id=foreign.id, position=2),
            RoutePlace(route_id=route.id, place_id=local[1].id, position=3),
        ]
    )
    db_session.commit()

    public = load_public_editorial_route_query(db_session).filter(Route.id == route.id).first()
    assert public is not None
    eligible_ids = {int(item.place_id) for item in public_editorial_route_places(db_session, public)}
    assert foreign.id not in eligible_ids
    assert eligible_ids == {local[0].id, local[1].id}

    started = client.post(f"/routes/{route.id}/sessions", json={"user_key": "web:p3"})
    assert started.status_code == 200
    point_ids = {row["place_id"] for row in started.json()["points"]}
    assert foreign.id not in point_ids
    assert point_ids == {local[0].id, local[1].id}
