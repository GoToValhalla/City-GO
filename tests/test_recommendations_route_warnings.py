from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.recommendations import router
from services.route_finalize_service import FinalRoute


def _fake_get_db():
    yield MagicMock()


def test_recommendation_route_exposes_warning_explanation_fields() -> None:
    warning = "Не нашли мест рядом с выбранным стартом."
    builder = MagicMock()
    builder.build_route.return_value = FinalRoute(
        route_id="route",
        points=[],
        total_minutes=0,
        total_places=0,
        estimated_distance=0.0,
        has_warnings=True,
        warning_count=1,
        warnings=[warning],
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _fake_get_db

    with patch("routers.recommendations.RouteBuilderService", return_value=builder):
        response = TestClient(app).post(
            "/recommendations/route",
            json={"lat": 54.96, "lng": 20.48, "time_budget_minutes": 120},
        )

    data = response.json()
    assert response.status_code == 200
    assert data["warnings"] == [warning]
    assert data["explanation"]["warnings"] == [warning]
    assert data["explanation"]["data_limitations"] == [warning]
