"""CITYGO Stage 3 / DEFECT 5: evaluation coverage for inventored public surfaces.

Uses FastAPI TestClient entrypoints so auth/session and public loaders are
exercised exactly as HTTP clients see them. Telegram is omitted: it calls the
same canonical HTTP APIs and has no independent candidate source.
"""

from __future__ import annotations

from models.city import City
from models.route import Route
from models.route_draft import RouteDraft
from models.route_place import RoutePlace
from schemas.user_route import UserRouteBuildRequest
from services.user_route_build_service import UserRouteBuildService
from tests.route_evaluation.invariants import run_all_point_invariants
from tests.route_evaluation.scenarios import (
    build_closed_status_city,
    build_healthy_compact_city,
    build_public_hidden_category_city,
)

GENERATION_RUN_ID = "citygo-stage3-surfaces-v1"
TOKEN = "eval-draft-session-token"


def test_eval_editorial_and_route_places_boundary_new(
    client, db_session, city_factory, published_place_factory
):
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    city = db_session.query(City).filter(City.slug == scenario.city_slug).one()
    route = Route(city_id=city.id, slug="eval-editorial-route", title="Eval", is_active=True)
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    for index, place_id in enumerate(scenario.eligible_place_ids[:3], start=1):
        db_session.add(RoutePlace(route_id=route.id, place_id=place_id, position=index))
    db_session.commit()

    detail = client.get(f"/routes/{route.id}")
    places = client.get("/route-places/", params={"route_id": route.id})
    assert detail.status_code == 200
    assert places.status_code == 200
    point_ids = {row["place_id"] for row in detail.json()["points"]}
    assert point_ids.issubset(set(scenario.eligible_place_ids))
    assert len(point_ids) >= 2


def test_eval_closed_and_hidden_categories_never_leak_new(
    db_session, city_factory, published_place_factory, place_factory
):
    for builder in (build_closed_status_city, build_public_hidden_category_city):
        scenario = builder(city_factory, published_place_factory, place_factory)
        request = UserRouteBuildRequest(
            lat=54.9611,
            lng=20.4703,
            city_id=scenario.city_slug,
            user_id=f"eval-{scenario.scenario_id}",
            build_mode="auto",
            time_budget_minutes=180,
            interests=[],
        )
        final = UserRouteBuildService().build(db=db_session, request=request)
        run_all_point_invariants(
            db_session,
            final,
            scenario_id=scenario.scenario_id,
            entrypoint="POST /v1/user-routes/build",
            build_mode="auto",
            expected_status="ready_or_partial",
            expected_city_slug=scenario.city_slug,
            generation_run_id=GENERATION_RUN_ID,
        )
        returned = {int(point.place_id) for point in final.points}
        assert returned.isdisjoint(set(scenario.ineligible_place_ids))


def test_eval_random_draft_access_and_stale_point_new(
    client, db_session, city_factory, published_place_factory
):
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    created = client.post(
        "/routes/random",
        json={
            "city_slug": scenario.city_slug,
            "budget_minutes": 120,
            "start": {"type": "city_center"},
            "category_mode": "none",
            "selected_category_slugs": [],
            "seed": 3,
            "session_token": TOKEN,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert "session_token" not in body
    draft_id = body["draft_id"]
    headers = {"X-Route-Draft-Session": TOKEN}

    assert client.get(f"/routes/drafts/{draft_id}", headers=headers).status_code == 200
    assert client.get(
        f"/routes/drafts/{draft_id}", headers={"X-Route-Draft-Session": "wrong-token-xx"}
    ).status_code == 404

    draft = db_session.query(RouteDraft).filter(RouteDraft.id == draft_id).one()
    if not draft.points:
        return
    place = draft.points[0].place
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_route_eligible = False
    place.publication_status = "draft"
    stale_id = place.id
    version_before = int(draft.version)
    point_count = len(draft.points)
    db_session.commit()
    refreshed = client.get(f"/routes/drafts/{draft_id}", headers=headers)
    assert refreshed.status_code == 200
    assert stale_id not in {point["place_id"] for point in refreshed.json()["points"]}
    db_session.expire_all()
    persisted = db_session.query(RouteDraft).filter(RouteDraft.id == draft_id).one()
    assert int(persisted.version) == version_before
    assert len(persisted.points) == point_count


def test_eval_legacy_replan_cannot_inject_ineligible_place_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    city = db_session.query(City).filter(City.slug == scenario.city_slug).one()
    bad = place_factory(
        slug="eval-replan-bank",
        city_id=city.id,
        category="bank",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=False,
        publication_status="published",
        lat=54.9620,
        lng=20.4710,
    )
    good_ids = scenario.eligible_place_ids[:2]
    response = client.post(
        "/routes/replan",
        json={
            "current_route": {
                "city_slug": scenario.city_slug,
                "route_mode": "walk",
                "points": [
                    {"place_id": good_ids[0], "position": 1},
                    {"place_id": good_ids[1], "position": 2},
                    {"place_id": bad.id, "position": 3},
                ],
                "remaining_time_minutes": 120,
            },
            "reason_type": "shorten_route",
            "preferred_stop_place_id": bad.id,
            "current_lat": 54.9611,
            "current_lng": 20.4703,
        },
    )
    assert response.status_code == 200
    returned_ids = {int(point["place_id"]) for point in response.json().get("points") or []}
    assert bad.id not in returned_ids
