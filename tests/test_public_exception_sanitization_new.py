"""Public 5xx responses must not leak exception internals."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.safe_errors import install_public_exception_handlers


def test_unhandled_exception_is_sanitized_new() -> None:
    app = FastAPI()
    install_public_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret-db-connection-string")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    detail = body["detail"]
    assert detail["code"] == "INTERNAL_ERROR"
    assert "secret-db-connection-string" not in response.text
    assert "RuntimeError" not in response.text
    assert detail.get("request_id")
