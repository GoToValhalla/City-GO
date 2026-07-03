from __future__ import annotations

import pytest

from scripts import production_smoke
from scripts import route_public_contract_gate as gate


def _public_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "warnings": ["Маршрут собран."],
        "user_warnings": [{"type": "route", "user_message": "Маршрут собран."}],
        "explanation": {"warnings": ["Маршрут собран."], "route_builder_v2": {"mode": "Быстрый маршрут"}},
        "debug_trace": [{"message": "Preview route build failed."}],
    }
    payload.update(updates)
    return payload


def test_route_public_contract_gate_user_facing_fields_match_production_smoke_new() -> None:
    assert gate.USER_FACING_ROUTE_FIELDS == production_smoke.USER_FACING_ROUTE_FIELDS


@pytest.mark.parametrize("field", gate.USER_FACING_ROUTE_FIELDS)
def test_route_public_contract_gate_catches_raw_code_in_every_user_facing_field_new(field: str) -> None:
    payload = _public_payload()
    if field == "warnings":
        payload[field] = ["route_builder_v2_insufficient_points"]
    elif field == "user_warnings":
        payload[field] = [{"type": "route", "user_message": "route_builder_v2_insufficient_points"}]
    elif field == "user_explanation":
        payload[field] = {"message": "route_builder_v2_insufficient_points"}
    elif field == "explanation":
        payload[field] = {"warnings": ["route_builder_v2_insufficient_points"]}

    assert gate._validate_public_payload(payload) == [f"raw technical code leaked at {field if field != 'user_warnings' else 'user_warnings[0].user_message'}"]


@pytest.mark.parametrize(
    "warning_type",
    ["route_builder_v2_insufficient_points", "budget_trim", "data_contract", "raw-debug"],
)
def test_route_public_contract_gate_rejects_non_public_warning_type_new(warning_type: str) -> None:
    payload = _public_payload(user_warnings=[{"type": warning_type, "user_message": "Маршрут собран."}])

    failures = gate._validate_public_payload(payload)

    assert f"user_warnings[0].type is not public: {warning_type}" in failures


@pytest.mark.parametrize("warning_type", sorted(gate.PUBLIC_WARNING_TYPES))
def test_route_public_contract_gate_accepts_public_warning_types_new(warning_type: str) -> None:
    payload = _public_payload(user_warnings=[{"type": warning_type, "user_message": "Маршрут собран."}])

    assert gate._validate_public_payload(payload) == []


@pytest.mark.parametrize(
    "message",
    ["", "route_builder_v2_insufficient_points", "unknown_internal_code"],
)
def test_route_public_contract_gate_rejects_empty_or_raw_user_warning_message_new(message: str) -> None:
    payload = _public_payload(user_warnings=[{"type": "route", "user_message": message}])

    failures = gate._validate_public_payload(payload)

    assert f"user_warnings[0].user_message is not user-facing: {message}" in failures


@pytest.mark.parametrize(
    "diagnostic",
    [
        "SECRET_TOKEN=super-secret-preview-token",
        "Authorization: Bearer private-token",
        "password=12345",
        "DATABASE_URL=postgres://internal-db",
        "sqlite:///./prod.db",
        "Traceback (most recent call last): ...",
    ],
)
def test_route_public_contract_gate_catches_sensitive_debug_trace_new(diagnostic: str) -> None:
    payload = _public_payload(debug_trace=[{"message": diagnostic}])

    failures = gate._validate_public_payload(payload)

    assert failures == ["sensitive diagnostic detail leaked at debug_trace[0].message"]


def test_route_public_contract_gate_accepts_sanitized_debug_trace_new() -> None:
    payload = _public_payload(debug_trace=[{"message": "Preview route build failed."}])

    assert gate._validate_public_payload(payload) == []


def test_route_public_contract_gate_requires_user_warning_objects_new() -> None:
    payload = _public_payload(user_warnings=["not-an-object"])

    assert gate._validate_public_payload(payload) == ["user_warnings[0] is not an object"]


def test_route_public_contract_gate_sample_payloads_are_clean_new() -> None:
    for name, payload in gate._sample_payloads().items():
        assert gate._validate_public_payload(payload) == [], name
