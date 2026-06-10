from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.user_routes import router
from schemas.user_route import UserRouteIntent, UserRouteState


def _fake_get_db():
    yield MagicMock()


def _state() -> UserRouteState:
    return UserRouteState(
        route_id="route",
        context=UserRouteIntent(lat=54.96, lng=20.48),
        total_places=0,
        total_minutes=0,
        total_estimated_minutes=0,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
    )


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[get_db] = _fake_get_db
    return app


def test_build_user_route_endpoint() -> None:
    service = MagicMock()
    service.build.return_value = _state()
    with patch("routers.user_routes.UserRouteBuildService", return_value=service):
        response = TestClient(_app()).post("/v1/user-routes/build", json={"lat": 54.96, "lng": 20.48})
    assert response.status_code == 200
    assert response.json()["route_id"] == "route"


def test_correct_user_route_endpoint() -> None:
    service = MagicMock()
    service.correct.return_value = _state()
    payload = {"current_route": _state().model_dump(), "action": "shorten_route"}
    with patch("routers.user_routes.UserRouteCorrectService", return_value=service):
        response = TestClient(_app()).post("/v1/user-routes/correct", json=payload)
    assert response.status_code == 200
    assert response.json()["route_id"] == "route"
