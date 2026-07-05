"""Security matrix: authz для read-only Data Pipeline."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

_VALID = "pipeline-security-token"
_AUTH = {"Authorization": f"Bearer {_VALID}"}
_WRONG = {"Authorization": "Bearer wrong-token"}


@pytest.fixture(autouse=True)
def _admin_token(monkeypatch):
    from core.config import settings

    monkeypatch.setattr(settings, "admin_api_token", _VALID)


def test_data_pipeline_without_auth_returns_401_new() -> None:
    assert TestClient(app).get("/admin/data-pipeline/status").status_code == 401


def test_data_pipeline_wrong_token_returns_403_new() -> None:
    assert TestClient(app).get("/admin/data-pipeline/status", headers=_WRONG).status_code == 403


def test_data_pipeline_valid_token_returns_200_new(override_get_db) -> None:
    response = TestClient(app).get("/admin/data-pipeline/status", headers=_AUTH)
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"overall_status", "metrics", "queues", "recent_runs", "fetched_at"}


@pytest.mark.parametrize("method", ["post", "put", "patch"])
def test_data_pipeline_has_no_write_methods_new(method) -> None:
    client = TestClient(app)
    response = getattr(client, method)("/admin/data-pipeline/status", headers=_AUTH, json={})
    assert response.status_code in {401, 403, 404, 405}


def test_data_pipeline_delete_not_allowed_new() -> None:
    response = TestClient(app).delete("/admin/data-pipeline/status", headers=_AUTH)
    assert response.status_code in {401, 403, 404, 405}
