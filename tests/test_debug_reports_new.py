from __future__ import annotations

from models.debug_report import DebugReport


def test_debug_report_stores_sanitized_payload_new(client, db_session):
    response = client.post(
        "/debug-reports",
        json=_payload(
            request_payload={
                "headers": {"Authorization": "Bearer secret", "Cookie": "sid=1"},
                "lat": 54.123456,
            }
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert "admin_url" not in body
    assert "telegram_error" not in body
    assert body["status"] == "accepted"
    row = db_session.query(DebugReport).filter_by(public_id=body["public_id"]).one()
    assert row.request_payload["headers"]["Authorization"] == "[REDACTED]"
    assert row.request_payload["headers"]["Cookie"] == "[REDACTED]"


def test_debug_report_rounds_precise_location_by_default_new(client, db_session):
    client.post(
        "/debug-reports",
        json=_payload(location_context={"lat": 54.123456, "lng": 20.654321, "location_source": "user"}),
    )
    row = db_session.query(DebugReport).one()
    assert row.location_context["lat"] == 54.12
    assert row.location_context["lng"] == 20.65


def test_debug_report_can_keep_route_trace_and_import_context_new(client, db_session):
    client.post(
        "/debug-reports",
        json=_payload(
            category="route",
            debug_trace={"retrieval": {"raw": 10}},
            warnings=["short"],
            reason_codes=["LOW_QUALITY"],
            backend_context={"city_admin_import_job_id": 9},
        ),
    )
    row = db_session.query(DebugReport).one()
    assert row.debug_trace == {"retrieval": {"raw": 10}}
    assert row.warnings == ["short"]
    assert row.backend_context == {"city_admin_import_job_id": 9}


def test_debug_report_telegram_disabled_by_default_new(client, db_session, monkeypatch):
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", False)
    response = client.post("/debug-reports", json=_payload())
    assert response.json()["telegram_status"] == "queued"
    row = db_session.query(DebugReport).one()
    assert row.telegram_sent is False


def test_debug_report_telegram_called_when_enabled_new(client, monkeypatch):
    calls = []
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", True)
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_chat_id", "debug-chat")
    monkeypatch.setattr(
        "services.debug_report_service.send_admin_alert",
        lambda **kwargs: calls.append(kwargs) or {"sent": True},
    )
    response = client.post("/debug-reports", json=_payload(category="import", backend_context={"import_job_id": 9}))
    assert response.json()["telegram_status"] == "sent"
    assert calls[0]["job_id"] == 9
    assert calls[0]["chat_id_override"] == "debug-chat"
    assert "Report:" in calls[0]["message"]


def test_debug_report_telegram_failure_does_not_break_creation_new(client, db_session, monkeypatch):
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", True)
    monkeypatch.setattr(
        "services.debug_report_service.send_admin_alert",
        lambda **kwargs: {"sent": False, "reason": "timeout"},
    )
    response = client.post("/debug-reports", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["telegram_status"] == "queued"
    assert "telegram_error" not in body
    row = db_session.query(DebugReport).one()
    assert row.telegram_error == "timeout"


def test_debug_report_telegram_success_returns_explicit_status_new(client, monkeypatch):
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", True)
    monkeypatch.setattr("services.debug_report_service.send_admin_alert", lambda **kwargs: {"sent": True})
    response = client.post("/debug-reports", json=_payload())
    body = response.json()
    assert body["telegram_status"] == "sent"
    assert "telegram_error" not in body


def test_debug_report_telegram_disabled_returns_explicit_reason_new(client, db_session, monkeypatch):
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", False)
    response = client.post("/debug-reports", json=_payload())
    body = response.json()
    assert body["telegram_status"] == "queued"
    assert "telegram_error" not in body
    row = db_session.query(DebugReport).one()
    assert row.telegram_error == "telegram_disabled"


def test_debug_report_telegram_failure_is_logged_with_context_new(client, db_session, monkeypatch):
    monkeypatch.setattr("services.debug_report_service.settings.citygo_debug_reports_telegram_enabled", True)
    monkeypatch.setattr(
        "services.debug_report_service.send_admin_alert",
        lambda **kwargs: {"sent": False, "reason": "timeout"},
    )

    response = client.post("/debug-reports", json=_payload(city_slug="zelenogradsk", request_id="req-log-1"))

    assert response.status_code == 200
    from models.system_log import SystemLog

    log = db_session.query(SystemLog).filter(SystemLog.module == "debug_report").order_by(SystemLog.id.desc()).first()
    assert log is not None
    assert log.city_slug == "zelenogradsk"
    assert log.request_id == "req-log-1"
    assert "timeout" in log.message


def test_admin_debug_reports_list_detail_and_filters_new(client):
    first = client.post("/debug-reports", json=_payload(city_slug="zelenogradsk", screen="route", request_id="req-1")).json()
    client.post("/debug-reports", json=_payload(city_slug="yerevan", screen="places", request_id="req-2"))
    listed = client.get("/admin/debug-reports", params={"city_slug": "zelenogradsk", "screen": "route", "request_id": "req-1"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    detail = client.get(f"/admin/debug-reports/{first['public_id']}")
    assert detail.status_code == 200
    assert detail.json()["request_id"] == "req-1"


def _payload(**overrides):
    base = {
        "screen": "route",
        "severity": "warning",
        "category": "route",
        "city_slug": "zelenogradsk",
        "request_id": "cg_req",
        "url": "https://citygo.example/routes?debug=1",
        "title": "Route problem",
        "summary": "1 point, warnings present",
        "browser": {"user_agent": "test"},
    }
    return base | overrides
