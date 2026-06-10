"""
Smoke-тест POST /recommendations/route: моки RouteBuilderService и ExplainabilityService.

Не поднимает полный pipeline, БД и PostGIS — только HTTP-слой и контракт JSON.

Запуск (как и для остальных router-тестов):
  python3 -m pytest tests/test_recommendations_route_router.py -q
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.recommendations import router as recommendations_router
from services.route_assembly_service import RoutePoint
from services.route_finalize_service import FinalRoute

# Тот же текст, что поднимает finalize для visit_duration validation (контракт ответа).
_VISIT_DURATION_ROUTE_WARNING = "Для некоторых мест использовано приблизительное время визита."


def _fake_get_db():
    """Заглушка Session для Depends(get_db), без реального подключения."""
    yield MagicMock()


def _minimal_app() -> FastAPI:
    """Минимальное приложение только с recommendations — без импорта main.app."""
    app = FastAPI()
    app.include_router(recommendations_router)
    return app


def test_post_recommendations_route_200_and_json_shape() -> None:
    """Успешный POST, 200, ожидаемые поля тела и summary внутри explanation."""
    app = _minimal_app()
    pt = RoutePoint(
        place_id="99",
        lat=55.0,
        lng=20.0,
        score=0.9,
        category="cafe",
        visit_minutes=25,
        opening_hours=None,
        title="Кофейня",
        address="ул. Курортная",
        image_url="https://img",
    )
    pt.estimated_walk_minutes = 5
    pt.estimated_arrival_time = datetime(2030, 1, 1, 10, 0, 0)
    pt.estimated_departure_time = datetime(2030, 1, 1, 10, 25, 0)
    pt.time_status = "ok"
    pt.time_warning = None

    final = FinalRoute(
        route_id="mock-route-id",
        points=[pt],
        total_minutes=25,
        total_places=1,
        estimated_distance=0.5,
        total_estimated_minutes=30,
        estimated_end_time=datetime(2030, 1, 1, 10, 25, 0),
        has_warnings=False,
        warning_count=0,
        places_with_warnings=[],
        warnings=[_VISIT_DURATION_ROUTE_WARNING],
        pipeline_trace=[{"stage": "candidate_retrieval", "count": 3}],
    )

    mock_builder = MagicMock()
    mock_builder.build_route.return_value = final

    mock_expl = MagicMock()
    mock_expl.build_route_explanation.return_value = {
        "route_id": "mock-route-id",
        "summary": "Маршрут на 1 точку, примерно 30 мин и 0.5 км.",
        "has_warnings": False,
        "warning_count": 0,
        "points": [
            {
                "place_id": "99",
                "reason": "test",
                "warning": None,
                "time_status": "ok",
            }
        ],
    }

    app.dependency_overrides[get_db] = _fake_get_db

    try:
        with patch(
            "routers.recommendations.RouteBuilderService",
            return_value=mock_builder,
        ), patch(
            "routers.recommendations.ExplainabilityService",
            return_value=mock_expl,
        ):
            client = TestClient(app)
            response = client.post(
                "/recommendations/route",
                json={
                    "lat": 55.0,
                    "lng": 20.0,
                    "time_budget_minutes": 120,
                    "interests": [],
                    "excluded_place_ids": [],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    data = response.json()

    assert "route_id" in data
    assert "points" in data
    assert "explanation" in data
    assert "_trace" not in data

    assert data["route_id"] == "mock-route-id"
    assert isinstance(data["points"], list)
    assert len(data["points"]) == 1
    assert data["points"][0]["place_id"] == "99"
    assert data["points"][0]["title"] == "Кофейня"
    assert data["points"][0]["address"] == "ул. Курортная"
    assert data["points"][0]["image_url"] == "https://img"

    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    assert data["warnings"] == [_VISIT_DURATION_ROUTE_WARNING]

    assert isinstance(data["explanation"], dict)
    assert "summary" in data["explanation"]
    assert data["explanation"]["summary"]
    assert data["explanation"]["route_id"] == "mock-route-id"


def test_post_recommendations_route_debug_trace_header() -> None:
    app = _minimal_app()
    final = FinalRoute("debug-route", [], 0, 0, 0.0,
                       pipeline_trace=[{"stage": "hard_filter", "kept_count": 1}])
    mock_builder = MagicMock()
    mock_builder.build_route.return_value = final
    mock_expl = MagicMock()
    mock_expl.build_route_explanation.return_value = {"summary": "ok"}
    app.dependency_overrides[get_db] = _fake_get_db
    try:
        with patch("routers.recommendations.RouteBuilderService", return_value=mock_builder), patch(
            "routers.recommendations.ExplainabilityService", return_value=mock_expl
        ):
            response = TestClient(app).post(
                "/recommendations/route",
                headers={"X-Debug": "true"},
                json={"lat": 55.0, "lng": 20.0, "time_budget_minutes": 120},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    assert response.json()["_trace"][0]["stage"] == "hard_filter"
