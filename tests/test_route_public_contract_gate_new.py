from __future__ import annotations

from scripts import production_smoke
from scripts import route_public_contract_gate as gate


def test_route_public_contract_gate_user_facing_fields_match_production_smoke_new() -> None:
    assert gate.USER_FACING_ROUTE_FIELDS == production_smoke.USER_FACING_ROUTE_FIELDS


def test_route_public_contract_gate_catches_sensitive_debug_trace_new() -> None:
    payload = {
        "warnings": ["Маршрут не удалось предварительно собрать."],
        "user_warnings": [{"type": "route", "user_message": "Маршрут не удалось предварительно собрать."}],
        "explanation": {"warnings": ["Маршрут не удалось предварительно собрать."]},
        "debug_trace": [{"message": "SECRET_TOKEN=super-secret-preview-token postgres://internal-db"}],
    }

    failures = gate._validate_public_payload(payload)

    assert failures == ["sensitive diagnostic detail leaked at debug_trace[0].message"]


def test_route_public_contract_gate_accepts_sanitized_debug_trace_new() -> None:
    payload = {
        "warnings": ["Маршрут не удалось предварительно собрать."],
        "user_warnings": [{"type": "route", "user_message": "Маршрут не удалось предварительно собрать."}],
        "explanation": {"warnings": ["Маршрут не удалось предварительно собрать."]},
        "debug_trace": [{"message": "Preview route build failed."}],
    }

    assert gate._validate_public_payload(payload) == []
