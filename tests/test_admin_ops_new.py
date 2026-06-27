"""Тесты admin ops: overview, feature toggles, metrics, verification summary."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.config import settings


_VALID_TOKEN = "test-admin-secret-for-auth-tests"
_HEADERS = {"Authorization": f"Bearer {_VALID_TOKEN}"}


@pytest.fixture(autouse=True)
def _admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _VALID_TOKEN)


def test_admin_overview_success_new(client: TestClient) -> None:
    response = client.get("/admin/overview", headers=_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "critical" in body
    assert "data_quality" in body


def test_feature_toggles_list_global_new(client: TestClient) -> None:
    response = client.get("/admin/feature-toggles?scope=global", headers=_HEADERS)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 5


def test_feature_toggle_update_new(client: TestClient) -> None:
    response = client.put(
        "/admin/feature-toggles/maintenance_mode?scope=global",
        headers=_HEADERS,
        json={"value_bool": True, "reason": "test"},
    )
    assert response.status_code == 200
    assert response.json()["value_bool"] is True


def test_verification_summary_new(client: TestClient) -> None:
    response = client.get("/admin/place-verifications/summary", headers=_HEADERS)
    assert response.status_code == 200
    assert "queue_total" in response.json()


def test_verification_queue_shape_new(client: TestClient, place_factory) -> None:
    place = place_factory(title="Парк")
    place.verification_status = "unverified"
    response = client.get("/admin/place-verifications/queue", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert {"items", "total", "limit", "offset"} <= set(body)
    assert any(item["place_id"] == place.id and item["title"] == "Парк" for item in body["items"])


def test_verification_stats_optional_city_new(client: TestClient, city_factory) -> None:
    city_factory(slug="khanty-mansiysk", name="Ханты-Мансийск")
    response = client.get("/admin/place-verifications/stats", headers=_HEADERS)
    assert response.status_code == 200
    assert response.json()["city_slug"] == "khanty-mansiysk"
