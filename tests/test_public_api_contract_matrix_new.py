"""Contract / negative / equivalence tests для публичного API мест."""

from __future__ import annotations

import pytest


DANGEROUS_PIPELINE_KEYS = {
    "step_details",
    "locked_by",
    "last_error",
    "job_id",
    "payload",
    "resolved_by",
}

REQUIRED_PUBLIC_KEYS = {"id", "slug", "title", "lat", "lng", "category"}


@pytest.mark.parametrize("limit", [1, 5, 20])
def test_places_list_contract_shape_new(client, limit) -> None:
    response = client.get("/places/", params={"city_slug": "zelenogradsk", "limit": limit})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("items"), list)
    assert isinstance(body.get("total"), int)
    assert body.get("limit") == limit
    assert body.get("offset") == 0


def test_places_search_requires_query_param_new(client) -> None:
    response = client.get("/places/search/", params={"city_slug": "zelenogradsk"})
    assert response.status_code in {400, 422}


def test_public_places_contract_stable_fields_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="contract-city", name="Contract", launch_status="published")
    place_factory(city_id=city.id, slug="contract-cafe", title="Contract Cafe", category="cafe")
    response = client.get("/places/", params={"city_slug": city.slug, "limit": 5})
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert REQUIRED_PUBLIC_KEYS.issubset(item.keys())
        assert not DANGEROUS_PIPELINE_KEYS.intersection(item.keys())


def test_pharmacy_rejected_in_route_dry_run_matrix_new(client, city_factory, place_factory) -> None:
    from types import SimpleNamespace
    from unittest.mock import patch

    from models.city import City
    from services.route_assembly_service import RoutePoint
    from services.route_generation_diagnostics.record import record_canonical_generation

    city = city_factory(slug="contract-pharm", name="Pharm city", launch_status="published")
    place_factory(city_id=city.id, slug="tourist-cafe", category="cafe", title="Cafe")
    place_factory(city_id=city.id, slug="service-pharm", category="pharmacy", title="Pharmacy")

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
        city_row = db.query(City).filter(City.slug == request.city_id).first()
        final.generation_run_id = record_canonical_generation(
            db,
            city=city_row,
            ctx=request,
            request_payload={"source": "test"},
            final_route=final,
        )
        return final

    with patch("services.route_builder_service.RouteBuilderService.build_route", _fake_build):
        response = client.post(
            "/admin/routes/dry-run",
            json={"city_slug": city.slug, "duration_min": 120, "route_mode": "walk"},
        )
    assert response.status_code == 200
    rejected_categories = {row.get("category") for row in response.json()["rejected_candidates"]}
    assert "pharmacy" in rejected_categories
