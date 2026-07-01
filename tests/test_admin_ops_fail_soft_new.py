from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

import routers.admin_ops as admin_ops


def test_admin_overview_degrades_to_json_when_db_query_fails(client, monkeypatch):
    def fail(_db):
        raise SQLAlchemyError("statement timeout")

    monkeypatch.setattr(admin_ops, "build_admin_overview", fail)

    response = client.get("/admin/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["critical"][0]["code"] == "admin_overview_degraded"
    assert payload["data_quality"] == []
    assert payload["operations"] == []


def test_admin_metrics_degrades_to_json_when_db_query_fails(client, monkeypatch):
    def fail(_db):
        raise SQLAlchemyError("statement timeout")

    monkeypatch.setattr(admin_ops, "build_metrics_summary", fail)

    response = client.get("/admin/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["routes_built"] == 0
    assert payload["places_total"] == 0
    assert "degraded" in payload["data_collection_note"].lower()


def test_admin_coverage_degrades_to_json_when_db_query_fails(client, monkeypatch):
    def fail(_db, *, limit, offset):
        raise SQLAlchemyError("statement timeout")

    monkeypatch.setattr(admin_ops, "build_coverage_summary", fail)

    response = client.get("/admin/coverage/summary?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"items": [], "total": 0, "limit": 5, "offset": 0}


def test_admin_verification_summary_degrades_to_json_when_db_query_fails(client, monkeypatch):
    def fail(_db):
        raise SQLAlchemyError("statement timeout")

    monkeypatch.setattr(admin_ops, "verification_queue_summary", fail)

    response = client.get("/admin/place-verifications/summary")

    assert response.status_code == 200
    assert response.json() == {
        "queue_total": 0,
        "needs_recheck": 0,
        "unverified": 0,
        "low_confidence": 0,
        "verified_today": 0,
    }
