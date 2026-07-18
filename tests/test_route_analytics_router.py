from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.dependencies import get_db
from models.route_build_event import RouteBuildEvent  # noqa: F401
from routers.route_analytics import router
from services.route_analytics_service import record_route_build
from tests.test_route_analytics_service import _route


def _app():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    RouteBuildEvent.__table__.create(bind=engine)
    db = sessionmaker(bind=engine)()
    with patch("services.route_analytics_service.SessionLocal", return_value=db):
        record_route_build(_route("r1", 0.7, []), source="api", latency_ms=10, user_id="u1")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return app


def test_route_analytics_summary_endpoint() -> None:
    response = TestClient(_app()).get("/route-analytics/summary")
    assert response.status_code == 200
    assert response.json()["total_routes"] == 1


def test_user_route_history_endpoint() -> None:
    response = TestClient(_app()).get("/route-analytics/users/u1/history")
    assert response.status_code == 200
    assert response.json()[0]["route_id"] == "r1"
