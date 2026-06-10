import json
import logging

from fastapi.testclient import TestClient

from main import app


def test_request_logging_writes_json_event(caplog) -> None:
    caplog.set_level(logging.INFO, logger="citygo.api.requests")
    response = TestClient(app).get("/health")
    data = json.loads(caplog.records[0].message)
    assert response.status_code == 200
    assert data["method"] == "GET"
    assert data["path"] == "/health"
    assert data["status_code"] == 200
    assert isinstance(data["duration_ms"], int)
