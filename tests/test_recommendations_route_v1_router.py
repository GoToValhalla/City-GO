from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.recommendations import router as recommendations_router
from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute


def _fake_get_db():
    yield MagicMock()


def test_v1_recommendations_route_alias_works() -> None:
    app = FastAPI()
    app.include_router(recommendations_router, prefix="/v1")
    app.dependency_overrides[get_db] = _fake_get_db

    point = RoutePoint("1", 55.0, 20.0, 0.9, "cafe", 25)
    final = FinalRoute("route-1", [point], 25, 1, 0.1, 25, datetime(2030, 1, 1, 10))
    builder = MagicMock()
    builder.build_route.return_value = final
    explainer = MagicMock()
    explainer.build_route_explanation.return_value = {"summary": "ok"}

    try:
        with patch("routers.recommendations.RouteBuilderService", return_value=builder), patch(
            "routers.recommendations.ExplainabilityService",
            return_value=explainer,
        ):
            response = TestClient(app).post(
                "/v1/recommendations/route",
                json={"lat": 55.0, "lng": 20.0, "time_budget_minutes": 120},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["route_id"] == "route-1"
