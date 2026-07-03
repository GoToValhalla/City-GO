from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.user_routes import router


def _fake_get_db():
    yield MagicMock()


class ExplodingRouteBuildService:
    def build(self, *, db, request):
        raise RuntimeError("SECRET_TOKEN=super-secret-preview-token postgres://internal-db")


def test_preview_route_does_not_leak_exception_message_in_public_debug_trace_new() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _fake_get_db

    with patch("routers.user_routes.UserRouteBuildService", return_value=ExplodingRouteBuildService()):
        response = TestClient(app).post(
            "/user-routes/preview",
            json={"lat": 43.238949, "lng": 76.889709, "city_id": "almaty", "time_budget_minutes": 120},
        )

    assert response.status_code == 200
    data = response.json()
    raw = json.dumps(data, ensure_ascii=False).casefold()

    assert data["status"] == "preview_failed"
    assert data["warnings"] == ["Маршрут не удалось предварительно собрать."]
    assert data["user_warnings"][0]["type"] == "route"
    assert "super-secret-preview-token" not in raw
    assert "postgres://internal-db" not in raw
    assert "secret_token" not in raw
    assert data["debug_trace"][0]["message"] == "Preview route build failed."
