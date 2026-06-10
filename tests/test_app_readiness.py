from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ok_when_database_is_ready() -> None:
    with patch("main.check_database_ready", return_value=(True, "ok")):
        response = TestClient(app).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ready_returns_503_when_database_is_not_ready() -> None:
    with patch("main.check_database_ready", return_value=(False, "OperationalError")):
        response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "OperationalError"}
