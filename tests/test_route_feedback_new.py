from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.route_feedback import router as route_feedback_router


class _FakeDb:
    """Минимальная Session-заглушка для router-теста без реальной БД."""

    def __init__(self) -> None:
        self.added = None
        self.committed = False

    def add(self, entity) -> None:
        self.added = entity
        entity.id = 1
        entity.created_at = datetime(2030, 1, 1, 12, 0, 0)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, entity) -> None:
        return None


def _client(fake_db: _FakeDb) -> TestClient:
    app = FastAPI()
    app.include_router(route_feedback_router)

    def _override_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_post_route_feedback_new_stores_signal() -> None:
    fake_db = _FakeDb()
    response = _client(fake_db).post(
        "/route-feedback/",
        json={"route_id": "route-1", "rating": 5, "source": "web"},
    )

    assert response.status_code == 200, response.text
    assert fake_db.committed is True
    assert fake_db.added.signal_type == "route_feedback"
    assert fake_db.added.entity_type == "route"
    assert fake_db.added.payload["rating"] == 5


def test_post_route_feedback_new_validates_rating() -> None:
    fake_db = _FakeDb()
    response = _client(fake_db).post(
        "/route-feedback/",
        json={"route_id": "route-1", "rating": 6},
    )

    assert response.status_code == 422
    assert fake_db.added is None
