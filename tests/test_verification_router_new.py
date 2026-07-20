"""Verification router requires admin auth; client fixture bypasses for happy-path."""

from fastapi.testclient import TestClient

from core.admin_auth import admin_required
from main import app


def test_v1_verification_queue_returns_city_places_new(client, city_factory, place_factory):
    city = city_factory(slug="verify-city", name="Город проверки")
    place_factory(slug="verify-place", title="Место проверки", city_id=city.id)

    response = client.get("/v1/verification/queue/verify-city")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["slug"] == "verify-place" for item in payload["items"])


def test_v1_verification_confirm_updates_place_new(client, city_factory, place_factory):
    city = city_factory(slug="confirm-city", name="Город подтверждения")
    place = place_factory(slug="confirm-place", title="Место подтверждения", city_id=city.id)

    response = client.post(
        f"/v1/verification/place/{place.id}/confirm",
        json={"action": "exists", "verifier": "field-tester", "comment": "Проверено на месте"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["place_id"] == place.id
    assert payload["verification_status"] == "verified"
    assert payload["existence_confidence_score"] == 100


def test_v1_verification_reject_marks_place_for_recheck_new(client, city_factory, place_factory):
    city = city_factory(slug="reject-city", name="Город отклонения")
    place = place_factory(slug="reject-place", title="Место отклонения", city_id=city.id)

    response = client.post(
        f"/v1/verification/place/{place.id}/reject",
        json={"action": "not_found", "verifier": "field-tester", "comment": "На месте объекта нет"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["place_id"] == place.id
    assert payload["verification_status"] == "not_found"
    assert payload["is_active"] is False


def test_v1_verification_stats_returns_city_summary_new(client, city_factory, place_factory):
    city = city_factory(slug="stats-city", name="Город статистики")
    place_factory(slug="stats-place", title="Место статистики", city_id=city.id)

    response = client.get("/v1/verification/stats/stats-city")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city_slug"] == "stats-city"
    assert payload["total_places"] >= 1


def test_v1_verification_requires_admin_without_bypass_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "admin_api_token", "verify-admin-token")
    app.dependency_overrides.pop(admin_required, None)
    try:
        response = TestClient(app).get("/v1/verification/queue/verify-city")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
