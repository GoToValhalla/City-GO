"""Тесты admin place ops: detail, create, bulk, system logs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.config import settings
from models.place import Place

_TOKEN = "test-admin-ops"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


@pytest.fixture(autouse=True)
def _token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _TOKEN)


def test_place_detail_new(client: TestClient, city_factory, db_session) -> None:
    city = city_factory(slug="detail-city", name="Detail")
    place = Place(city_id=city.id, slug="detail-p", title="Кафе", lat=1.0, lng=2.0, category="coffee",
                  publication_status="draft", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)
    db_session.add(place)
    db_session.commit()
    r = client.get(f"/admin/places/{place.id}/detail", headers=_HEADERS)
    assert r.status_code == 200
    assert r.json()["title"] == "Кафе"


def test_create_draft_new(client: TestClient, city_factory) -> None:
    city = city_factory(slug="create-city", name="Create")
    r = client.post("/admin/places/create-draft", headers=_HEADERS, json={
        "city_id": city.id, "title": "Новое место", "category": "museum", "lat": 10.0, "lng": 20.0,
    })
    assert r.status_code == 200
    assert r.json()["publication_status"] == "draft"


def test_bulk_preview_new(client: TestClient, city_factory, db_session) -> None:
    city = city_factory(slug="bulk-city", name="Bulk")
    p = Place(city_id=city.id, slug="bulk-p", title="X", lat=1.0, lng=2.0, category="walk")
    db_session.add(p)
    db_session.commit()
    r = client.post("/admin/places/bulk/preview", headers=_HEADERS, json={
        "place_ids": [p.id], "action": "set_category", "params": {"category": "museum"},
    })
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_system_logs_new(client: TestClient, db_session) -> None:
    from services.system_log_service import write_system_log
    write_system_log(db_session, level="error", module="test", message="smoke")
    r = client.get("/admin/system-logs", headers=_HEADERS)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_city_settings_new(client: TestClient, city_factory) -> None:
    city_factory(slug="settings-city", name="Settings")
    r = client.get("/admin/cities/settings-city/settings", headers=_HEADERS)
    assert r.status_code == 200
    assert r.json()["city_slug"] == "settings-city"
