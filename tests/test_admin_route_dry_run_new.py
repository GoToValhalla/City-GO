"""Тесты admin dry-run маршрутов."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from services.route_assembly_service import RoutePoint

try:  # pragma: no cover - локально allure может быть не установлен.
    import allure
except Exception:  # pragma: no cover
    allure = None


def _allure_story(name: str) -> None:
    if allure is not None:
        allure.dynamic.feature("Admin route dry-run")
        allure.dynamic.story(name)


def _fake_build(self, db, request, profile=None):  # noqa: ARG001
    from models.place import Place

    cafe = db.query(Place).filter(Place.category == "cafe").first()
    point = RoutePoint(
        place_id=str(cafe.id),
        lat=54.96,
        lng=20.47,
        score=0.9,
        category="museum",
        visit_minutes=30,
        title="Museum",
    )
    final = SimpleNamespace(points=[point], generation_run_id=None)
    from services.route_generation_diagnostics.record import record_canonical_generation
    from models.city import City

    city = db.query(City).filter(City.slug == request.city_id).first()
    final.generation_run_id = record_canonical_generation(
        db,
        city=city,
        ctx=request,
        request_payload={"source": "test"},
        final_route=final,
    )
    return final


def test_admin_dry_run_returns_candidates_new(client, db_session, city_factory, place_factory) -> None:
    _allure_story("Dry-run returns actionable selected and rejected candidates")
    city = city_factory(slug="dry-run-city")
    place_factory(slug="dry-cafe", category="cafe", city_id=city.id)
    place_factory(slug="dry-cafe-backup", category="cafe", city_id=city.id)
    place_factory(slug="dry-pharm", category="pharmacy", city_id=city.id)
    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_build):
        response = client.post(
            "/admin/routes/dry-run",
            json={
                "city_slug": city.slug,
                "duration_min": 120,
                "route_mode": "walk",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_run_id"] > 0
    assert body["counts"]["total_candidates"] >= 3
    rejected_categories = {row.get("category") for row in body["rejected_candidates"]}
    assert "pharmacy" in rejected_categories
    assert all(row["rejection_reasons"] for row in body["rejected_candidates"])
    assert any(
        "not_selected_lower_score" in row["rejection_reasons"]
        for row in body["rejected_candidates"]
        if row.get("category") == "cafe"
    )
