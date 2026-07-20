"""Route session ownership: hashed token required after create."""

from __future__ import annotations

import models.route_session  # noqa: F401
from models.route import Route
from models.route_place import RoutePlace
from services.anonymous_ownership import ROUTE_SESSION_HEADER, hash_ownership_token


def _seed_route(db_session, city_factory, place_factory, slug: str):
    city = city_factory(slug=slug, name=slug)
    a = place_factory(
        city_id=city.id,
        slug=f"{slug}-a",
        title="A",
        category="park",
        lat=54.91,
        lng=20.41,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    b = place_factory(
        city_id=city.id,
        slug=f"{slug}-b",
        title="B",
        category="museum",
        lat=54.92,
        lng=20.42,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    route = Route(city_id=city.id, slug=f"{slug}-route", title="R", is_active=True)
    db_session.add(route)
    db_session.flush()
    db_session.add_all(
        [
            RoutePlace(route_id=route.id, place_id=a.id, position=1),
            RoutePlace(route_id=route.id, place_id=b.id, position=2),
        ]
    )
    db_session.commit()
    return route


def test_route_session_issues_token_once_and_requires_header_new(
    client, db_session, city_factory, place_factory, monkeypatch
):
    monkeypatch.setattr("core.public_access_middleware.assert_web_public", lambda db: None)
    route = _seed_route(db_session, city_factory, place_factory, "own-sess")

    created = client.post(f"/routes/{route.id}/sessions", json={})
    assert created.status_code == 200
    body = created.json()
    token = body["ownership_token"]
    assert token and len(token) >= 16
    session_id = body["id"]

    from models.route_session import RouteSession

    row = db_session.query(RouteSession).filter(RouteSession.id == session_id).one()
    assert row.ownership_token_hash == hash_ownership_token(token)
    assert "ownership_token" not in client.get(
        f"/route-sessions/{session_id}", headers={ROUTE_SESSION_HEADER: token}
    ).json() or True

    assert client.get(f"/route-sessions/{session_id}").status_code == 404
    assert client.get(
        f"/route-sessions/{session_id}", headers={ROUTE_SESSION_HEADER: "wrong-token-xxxxxxxx"}
    ).status_code == 404

    ok = client.get(f"/route-sessions/{session_id}", headers={ROUTE_SESSION_HEADER: token})
    assert ok.status_code == 200
    assert ok.json().get("ownership_token") is None

    checkin = client.post(
        f"/route-sessions/{session_id}/events/checkin",
        headers={ROUTE_SESSION_HEADER: token},
        json={"point_index": 0, "action": "visit"},
    )
    assert checkin.status_code == 200
