from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def test_admin_quality_endpoint_forwards_safe_limit(
    client: TestClient,
    monkeypatch,
) -> None:
    """GET /admin/quality keeps the default read bounded without changing response shape."""
    calls: list[dict[str, Any]] = []

    def fake_quality_summary(db: Session, **kwargs: Any) -> dict[str, object]:
        calls.append(kwargs)
        return {"items": [], "total": 0, "todo": []}

    monkeypatch.setattr("routers.admin_platform.quality_summary", fake_quality_summary)

    response = client.get("/admin/quality")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "todo": []}
    assert calls == [{"city_slug": None, "region": None, "category": None, "severity": None, "limit": 5, "offset": 0}]


def test_admin_quality_endpoint_degrades_instead_of_failing(
    client: TestClient,
    monkeypatch,
) -> None:
    """Slow/failed admin quality reads must not take production smoke down."""

    def broken_quality_summary(db: Session, **kwargs: Any) -> dict[str, object]:
        raise SQLAlchemyError("statement timeout")

    monkeypatch.setattr("routers.admin_platform.quality_summary", broken_quality_summary)

    response = client.get("/admin/quality?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"items", "total", "todo"}
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["todo"]
