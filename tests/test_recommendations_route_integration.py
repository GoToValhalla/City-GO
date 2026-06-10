"""
Интеграционные тесты POST /recommendations/route (City Go).

Здесь намеренно НЕТ моков (ни patch, ни MagicMock): вызывается реальный FastAPI app
из main, реальная сессия БД через Depends(get_db) и полный pipeline
(RouteBuilderService → ExplainabilityService), как в продакшене.

Такие тесты требуют рабочую Postgres/PostGIS и данные кандидатов в БД — поэтому по умолчанию
они пропускаются, чтобы локальная разработка и CI без БД не ломались.

Включение (из корня репозитория), при корректном DATABASE_URL на PostgreSQL:

  RUN_RECOMMENDATIONS_INTEGRATION=1 python3.11 -m pytest tests/test_recommendations_route_integration.py -v

Без флага RUN_RECOMMENDATIONS_INTEGRATION=1 все тесты в этом файле будут skipped.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from core.config import settings
from main import app


def _integration_enabled() -> bool:
    """True только при явном флаге и реальной PostgreSQL-строке подключения (как DB smoke)."""
    if os.environ.get("RUN_RECOMMENDATIONS_INTEGRATION", "").strip() != "1":
        return False
    url = (settings.database_url or "").lower()
    return "postgresql" in url


# Условие skip вынесено в фикстуру, чтобы три теста не дублировали одну и ту же проверку окружения.
pytestmark = pytest.mark.skipif(
    not _integration_enabled(),
    reason=(
        "Интеграция выключена: задайте RUN_RECOMMENDATIONS_INTEGRATION=1 и postgresql* DATABASE_URL "
        "(см. модульный docstring)."
    ),
)


# Общий payload: координаты как в smoke retrieval; пустые интересы и исключения — типовой happy path.
def _happy_path_payload() -> dict:
    return {
        "lat": 54.96,
        "lng": 20.48,
        "time_budget_minutes": 120,
        "interests": [],
        "excluded_place_ids": [],
    }


def test_post_recommendations_route_happy_path_real_pipeline() -> None:
    """
    Happy path: полный HTTP → БД → pipeline → JSON.

    Ожидается непустая выдача кандидатов в БД для этих координат (как в рабочем retrieval smoke);
    иначе assert на len(points) зафейлится — это сигнал, что окружение без данных.
    """
    client = TestClient(app)
    response = client.post("/recommendations/route", json=_happy_path_payload())

    assert response.status_code == 200, response.text
    data = response.json()

    assert data.get("route_id"), "В ответе должен быть непустой route_id"
    assert "points" in data
    assert isinstance(data["points"], list)
    assert len(data["points"]) >= 1, "При непустой БД ожидается хотя бы одна точка маршрута"

    first = data["points"][0]
    assert "time_status" in first

    assert "warnings" in data
    assert isinstance(data["warnings"], list)

    assert "explanation" in data
    assert isinstance(data["explanation"], dict)
    assert "summary" in data["explanation"]
    assert data["explanation"]["summary"]


def test_post_recommendations_route_cold_start_no_profile_still_200() -> None:
    """
    Cold start: профиль пользователя endpoint не передаёт (в роутере profile=None).

    Отдельный сценарий от happy path: убеждаемся, что без профиля запрос не падает и возвращает маршрут.
    """
    client = TestClient(app)
    response = client.post("/recommendations/route", json=_happy_path_payload())

    assert response.status_code == 200, response.text
    data = response.json()

    assert "route_id" in data
    assert isinstance(data.get("points"), list)

    assert "warnings" in data
    assert isinstance(data["warnings"], list)


def test_post_recommendations_route_invalid_payload_missing_lat_lng_422() -> None:
    """Невалидное тело: без обязательных lat/lng — валидация FastAPI/Pydantic → 422."""
    client = TestClient(app)
    response = client.post(
        "/recommendations/route",
        json={
            "time_budget_minutes": 120,
            "interests": [],
            "excluded_place_ids": [],
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Запуск вручную (копипаст из корня репозитория):
#
#   python3.11 -m pytest tests/test_recommendations_route_integration.py -v
#
# С включением интеграции на реальной БД:
#
#   RUN_RECOMMENDATIONS_INTEGRATION=1 python3.11 -m pytest tests/test_recommendations_route_integration.py -v
# ---------------------------------------------------------------------------
