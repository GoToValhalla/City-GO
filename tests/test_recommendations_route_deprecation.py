from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.recommendations import CANONICAL_ROUTE_ENDPOINT, router
from services.route_finalize_service import FinalRoute


def _fake_get_db():
    yield MagicMock()


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[get_db] = _fake_get_db
    return app


def _post(path: str):
    builder = MagicMock()
    builder.build_route.return_value = FinalRoute("route", [], 0, 0, 0.0)
    with patch("routers.recommendations.RouteBuilderService", return_value=builder):
        return TestClient(_app()).post(
            path,
            json={"lat": 54.96, "lng": 20.48, "time_budget_minutes": 120},
        )


def test_legacy_recommendations_route_has_deprecation_headers() -> None:
    response = _post("/recommendations/route")
    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert CANONICAL_ROUTE_ENDPOINT in response.headers["Link"]


def test_v1_recommendations_route_is_not_deprecated() -> None:
    response = _post(CANONICAL_ROUTE_ENDPOINT)
    assert response.status_code == 200
    assert "Deprecation" not in response.headers
