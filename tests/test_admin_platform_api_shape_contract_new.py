from __future__ import annotations

from fastapi.testclient import TestClient


REQUIRED_QUALITY_ITEM_KEYS = {
    "city_slug",
    "city_name",
    "readiness_score",
    "stored_readiness_score",
    "places_total",
    "review_universe_total",
    "manual_review_total",
    "auto_excluded_total",
    "severity",
    "blockers",
    "primary_blocker",
    "critical_coverage",
}


def test_admin_system_health_shape_is_stable_new(client: TestClient) -> None:
    response = client.get("/admin/system-health")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["services"], list)
    assert isinstance(data["queues"], dict)
    assert isinstance(data["retention_days"], int)
    assert {"imports", "verification", "photos"} <= set(data["queues"])
    assert all({"name", "status", "description", "queue_depth"} <= set(service) for service in data["services"])


def test_admin_quality_shape_is_stable_for_city_with_places_new(client: TestClient, city_factory, place_factory) -> None:
    city = city_factory(slug="quality-city", name="Quality City")
    place_factory(city_id=city.id, slug="quality-place", title="Quality Place", category="museum", address="Main", image_url="https://example.com/photo.jpg")

    response = client.get("/admin/quality", params={"city_slug": city.slug})

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "todo"}
    assert data["total"] == 1
    assert isinstance(data["items"], list)
    assert REQUIRED_QUALITY_ITEM_KEYS <= set(data["items"][0])
    assert data["items"][0]["city_slug"] == city.slug
    assert isinstance(data["items"][0]["blockers"], dict)
    assert isinstance(data["items"][0]["critical_coverage"], dict)


def test_admin_quality_returns_empty_shape_not_500_for_unknown_city_new(client: TestClient) -> None:
    response = client.get("/admin/quality", params={"city_slug": "missing-city"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "todo": []}


def test_admin_taxonomy_categories_list_shape_has_items_and_total_new(client: TestClient, category_factory) -> None:
    category_factory(code="museum", name="Музей")

    response = client.get("/admin/taxonomy/categories", params={"limit": 1})

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_admin_taxonomy_categories_control_shape_has_categories_key_new(client: TestClient, city_factory, place_factory) -> None:
    city = city_factory(slug="taxonomy-city", name="Taxonomy City")
    place_factory(city_id=city.id, slug="taxonomy-place", title="Taxonomy Place", category="museum")

    response = client.get("/admin/taxonomy/categories", params={"city_slug": city.slug})

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)


def test_admin_analytics_shape_is_stable_new(client: TestClient) -> None:
    response = client.get("/admin/analytics")

    assert response.status_code == 200
    data = response.json()
    assert {"period_days", "metrics", "event_breakdown", "navigation", "availability"} <= set(data)
    assert isinstance(data["metrics"], dict)
    assert isinstance(data["event_breakdown"], list)
    assert isinstance(data["navigation"], dict)
    assert isinstance(data["availability"], dict)
