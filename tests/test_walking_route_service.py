import allure
import httpx
import pytest

from schemas.walking_route import WalkingRoutePoint
from services import walking_route_service
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.unit, pytest.mark.regression]


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("routing failed", request=httpx.Request("GET", "https://router"), response=httpx.Response(self.status_code))

    def json(self) -> dict:
        return self.payload


@scenario(
    "Карта получает пешеходную геометрию по улицам и понятные шаги",
    epic="Маршруты",
    feature="Построение и прохождение маршрута",
    story="Пешеходная навигация",
    severity=allure.severity_level.CRITICAL,
)
def test_walking_route_uses_provider_geometry_and_builds_instructions(monkeypatch) -> None:
    with given("провайдер вернул геометрию по дорожному графу и манёвры"):
        walking_route_service._cached_walking_route.cache_clear()
        payload = {
            "code": "Ok",
            "routes": [{
                "distance": 740.0,
                "duration": 560.0,
                "geometry": {"coordinates": [[48.04, 46.35], [48.041, 46.352], [48.045, 46.354]]},
                "legs": [{
                    "distance": 740.0,
                    "duration": 560.0,
                    "steps": [
                        {"distance": 300, "duration": 220, "name": "Советская улица", "maneuver": {"type": "depart"}},
                        {"distance": 440, "duration": 340, "name": "Набережная", "maneuver": {"type": "turn", "modifier": "right"}},
                        {"distance": 0, "duration": 0, "name": "", "maneuver": {"type": "arrive"}},
                    ],
                }],
            }],
        }
        monkeypatch.setattr(walking_route_service.httpx, "get", lambda *args, **kwargs: _Response(payload))

    with when("строится путь между двумя точками"):
        result = walking_route_service.build_walking_route([
            WalkingRoutePoint(lat=46.35, lng=48.04),
            WalkingRoutePoint(lat=46.354, lng=48.045),
        ])

    with then("используется геометрия провайдера, а не прямая между точками"):
        assert result.status == "routed"
        assert len(result.geometry) == 3
        assert result.geometry[1] == (48.041, 46.352)

    with then("пользователь получает русские инструкции и реальные метрики"):
        assert result.distance_meters == 740
        assert result.legs[0].steps[0].instruction == "Начните движение на Советская улица"
        assert result.legs[0].steps[1].instruction == "Поверните направо на Набережная"


@scenario(
    "При сбое роутера карта не рисует ложную прямую через здания",
    epic="Маршруты",
    feature="Построение и прохождение маршрута",
    story="Безопасная деградация карты",
    severity=allure.severity_level.CRITICAL,
)
def test_walking_route_failure_returns_no_geometry(monkeypatch) -> None:
    with given("пешеходный роутер недоступен"):
        walking_route_service._cached_walking_route.cache_clear()
        def fail(*args, **kwargs):
            raise httpx.ConnectError("offline")
        monkeypatch.setattr(walking_route_service.httpx, "get", fail)

    with when("frontend запрашивает геометрию маршрута"):
        result = walking_route_service.build_walking_route([
            WalkingRoutePoint(lat=46.35, lng=48.04),
            WalkingRoutePoint(lat=46.354, lng=48.045),
        ])

    with then("ответ не содержит прямой линии и объясняет причину"):
        assert result.status == "unavailable"
        assert result.geometry == []
        assert "не вести через здания" in (result.warning or "")
