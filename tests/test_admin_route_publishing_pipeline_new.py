"""Regression tests for admin route publishing pipeline."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from models.route import Route
from services.route_assembly_service import RoutePoint


def test_admin_route_dry_run_success_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-dry-run")
    place_factory(slug="pipeline-cafe", category="cafe", city_id=city.id)
    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_build):
        response = client.post("/admin/routes/dry-run", json={"city_slug": city.slug})
    assert response.status_code == 200
    assert response.json()["counts"]["selected_places"] == 1


def test_admin_route_dry_run_not_enough_eligible_places_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-no-route")
    place_factory(slug="pipeline-pharmacy", category="pharmacy", city_id=city.id)
    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_empty_build):
        response = client.post("/admin/routes/dry-run", json={"city_slug": city.slug})
    assert response.status_code == 200
    assert response.json()["counts"]["selected_places"] == 0


def test_admin_route_draft_creation_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-draft")
    place_factory(slug="draft-cafe", category="cafe", city_id=city.id)
    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_build):
        response = client.post("/admin/routes/drafts/generate", json={"city_slug": city.slug})
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["draft_id"] > 0
    assert len(body["draft"]["points"]) == 1
    assert body["dry_run"]["counts"]["selected_places"] == 1


def test_admin_route_publishing_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-publish")
    place_factory(slug="publish-cafe", category="cafe", city_id=city.id)
    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_build):
        draft = client.post("/admin/routes/drafts/generate", json={"city_slug": city.slug}).json()["draft"]
    response = client.post(
        f"/admin/routes/drafts/{draft['draft_id']}/publish",
        json={"title": "Admin Published Route", "slug": "admin-published-route"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"]["is_active"] is True
    assert body["route"]["slug"] == "admin-published-route"
    assert len(body["route"]["points"]) == 1
    assert db_session.query(Route).filter(Route.slug == "admin-published-route").count() == 1


def test_city_readiness_includes_published_routes_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-readiness")
    place_factory(slug="ready-cafe", category="cafe", city_id=city.id)
    route = Route(city_id=city.id, slug="ready-route", title="Ready Route", is_active=True)
    db_session.add(route)
    db_session.commit()
    response = client.get(f"/admin/routes/readiness/{city.slug}")
    assert response.status_code == 200
    components = response.json()["components"]
    assert components["eligible_places"] >= 1
    assert components["published_routes"] == 1
    assert components["has_published_routes"] == 1


def _fake_build(self, db, request, profile=None):  # noqa: ARG001
    place = _first_place(db, "cafe")
    point = RoutePoint(str(place.id), place.lat, place.lng, 0.9, place.category, 30, title=place.title)
    return _recorded_final(db, request, [point])


def _fake_empty_build(self, db, request, profile=None):  # noqa: ARG001
    return _recorded_final(db, request, [])


def _first_place(db, category: str):
    from models.place import Place

    return db.query(Place).filter(Place.category == category).first()


def _recorded_final(db, request, points: list[RoutePoint]):
    from models.city import City
    from services.route_generation_diagnostics.record import record_canonical_generation

    final = SimpleNamespace(points=points, generation_run_id=None, quality_score=0.7, warnings=[])
    city = db.query(City).filter(City.slug == request.city_id).first()
    final.generation_run_id = record_canonical_generation(db, city=city, ctx=request, request_payload={}, final_route=final)
    return final
