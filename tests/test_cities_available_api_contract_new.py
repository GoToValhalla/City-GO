from __future__ import annotations

from fastapi.testclient import TestClient

from models.city_admin_import_job import CityAdminImportJob


def _by_slug(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["slug"]): item for item in items}


def test_cities_available_api_returns_stable_catalog_shape_new(client: TestClient, city_factory, place_factory) -> None:
    city = city_factory(slug="api-city", name="API City", region="Region", country="Country")
    place_factory(city_id=city.id, slug="api-place", title="API Place", category="museum")

    response = client.get("/cities/available")

    assert response.status_code == 200
    rows = _by_slug(response.json())
    assert rows["api-city"] == {
        "slug": "api-city",
        "name": "API City",
        "country": "Country",
        "region": "Region",
        "launch_status": "published",
        "places_count": 1,
    }


def test_cities_available_api_counter_does_not_drop_route_ineligible_catalog_places_new(
    client: TestClient,
    city_factory,
    place_factory,
) -> None:
    city = city_factory(slug="api-counter", name="API Counter")
    place_factory(city_id=city.id, slug="route-ready", title="Route Ready", category="museum", is_route_eligible=True)
    place_factory(city_id=city.id, slug="catalog-only", title="Catalog Only", category="park", is_route_eligible=False)

    response = client.get("/cities/available")

    assert response.status_code == 200
    assert _by_slug(response.json())["api-counter"]["places_count"] == 2


def test_cities_available_api_is_unaffected_by_a_running_import_job_new(
    client: TestClient,
    db_session,
    city_factory,
    place_factory,
) -> None:
    """Public catalog reads must not depend on admin import/enrichment worker
    state — a city mid photo-enrichment (job.status="running") must still
    serve normally, proving no coupling between worker activity and this endpoint."""
    other_city = city_factory(slug="other-published-city", name="Other Published City")
    place_factory(city_id=other_city.id, slug="other-place", title="Other Place", category="museum")
    running_city = city_factory(slug="running-worker-city", name="Running Worker City")
    place_factory(city_id=running_city.id, slug="running-place", title="Running Place", category="museum")
    job = CityAdminImportJob(city_id=running_city.id, status="running", source="admin_photo_enrichment", current_step="finding_images")
    db_session.add(job)
    db_session.commit()

    response = client.get("/cities/available")

    assert response.status_code == 200
    rows = _by_slug(response.json())
    assert "other-published-city" in rows
    assert "running-worker-city" in rows
    assert rows["running-worker-city"]["places_count"] == 1
