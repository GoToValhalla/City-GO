from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.admin_auth import AdminContext, admin_required
from main import app
from schemas.place import PlaceRead


# Все тесты в этом модуле используют mocked services — auth bypassed через override.
@pytest.fixture(autouse=True)
def _bypass_admin_auth():
    """Обход admin auth для unit-тестов роутера (проверяем логику, не auth)."""
    app.dependency_overrides[admin_required] = lambda: AdminContext(
        actor_id="test-admin", actor_role="admin", auth_source="test"
    )
    yield
    app.dependency_overrides.pop(admin_required, None)


def _place_read() -> PlaceRead:
    return PlaceRead(
        id=1,
        city_id=1,
        category_id=None,
        slug="test-place",
        title="Тестовое место",
        short_description=None,
        lat=54.96,
        lng=20.47,
        outdoor=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        is_searchable=True,
        publication_status="published",
        existence_confidence_score=90,
        existence_confidence_level="high",
        verification_status="verified",
        created_at=datetime(2030, 1, 1),
        updated_at=datetime(2030, 1, 1),
    )


def test_admin_dashboard_endpoint_returns_russian_admin_metrics() -> None:
    with patch(
        "routers.admin.get_admin_dashboard",
        return_value={
            "cities_total": 1,
            "cities_published": 1,
            "places_total": 10,
            "places_published": 7,
            "places_hidden": 3,
            "places_needs_recheck": 2,
            "places_low_confidence": 1,
            "places_without_photo": 4,
            "pending_photos": 5,
            "routes_total": 2,
            "routes_active": 1,
        },
    ):
        response = TestClient(app).get("/admin/dashboard")

    assert response.status_code == 200
    assert response.json()["places_published"] == 7
    assert response.json()["pending_photos"] == 5


def test_admin_publish_place_endpoint_publishes_place() -> None:
    with (
        patch("routers.admin.publish_place", return_value=MagicMock()),
        patch("routers.admin.build_place_read", return_value=_place_read()),
    ):
        response = TestClient(app).post(
            "/admin/places/1/publish",
            json={"actor": "qa", "reason": "Проверено"},
        )

    assert response.status_code == 200
    assert response.json()["publication_status"] == "published"
    assert response.json()["is_visible_in_catalog"] is True


def test_admin_unpublish_place_requires_reason() -> None:
    response = TestClient(app).post("/admin/places/1/unpublish", json={"actor": "qa"})
    assert response.status_code == 422


def test_admin_city_import_endpoint_creates_import_request() -> None:
    city = MagicMock()
    city.id = 10
    city.slug = "kaliningrad"
    city.name = "Калининград"

    queued_job = MagicMock()
    queued_job.id = 55

    def fake_get_db():
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = queued_job
        yield db

    from db.dependencies import get_db

    app.dependency_overrides[get_db] = fake_get_db
    try:
        with patch("routers.admin.create_city_and_queue_import", return_value=city):
            response = TestClient(app).post(
                "/admin/cities/import",
                json={"name": "Калининград", "actor": "qa"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["job_status"] == "queued"
    assert "сбор мест" in response.json()["message"]


def test_admin_route_unpublish_endpoint_returns_route() -> None:
    route = MagicMock()
    route.id = 1
    route.city_id = 1
    route.slug = "walk"
    route.title = "Маршрут"
    route.short_description = None
    route.duration_minutes = 60
    route.distance_km = 2.5
    route.route_mode = "walk"
    route.is_active = False
    route.created_at = datetime(2030, 1, 1)
    route.updated_at = datetime(2030, 1, 1)

    with patch("routers.admin.unpublish_route", return_value=route):
        response = TestClient(app).post(
            "/admin/routes/1/unpublish",
            json={"actor": "qa", "reason": "Маршрут требует проверки"},
        )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
