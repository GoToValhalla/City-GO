"""CITYGO-360: public debug_trace must not leak sensitive diagnostics."""

from __future__ import annotations

import json

import pytest

from schemas.user_route import UserRouteIntent, UserRouteState
from scripts import route_public_contract_gate as gate
from services.public_route_sanitizer import sanitize_user_route_state


def _state_with_debug_trace(message: str) -> UserRouteState:
    return UserRouteState(
        route_id="route-debug",
        status="partial_route",
        context=UserRouteIntent(lat=40.0, lng=44.0, city_id="yerevan"),
        total_places=0,
        total_minutes=0,
        total_estimated_minutes=0,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.0,
        quality_status="weak",
        debug_trace=[{"stage": "assembly", "status": "failed", "message": message}],
    )


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
def test_public_route_sanitizer_strips_sensitive_debug_trace_new(diagnostic: str) -> None:
    sanitized = sanitize_user_route_state(_state_with_debug_trace(diagnostic))
    payload = sanitized.model_dump(mode="json")
    raw = json.dumps(payload, ensure_ascii=False).casefold()

    assert gate._validate_public_payload(payload) == []
    assert "super-secret" not in raw
    assert "private-token" not in raw
    assert "postgres://" not in raw
    assert "traceback" not in raw
    assert sanitized.debug_trace[0]["message"] == "Diagnostic detail suppressed."


def test_public_route_sanitizer_keeps_safe_preview_debug_message_new() -> None:
    sanitized = sanitize_user_route_state(_state_with_debug_trace("Preview route build failed."))
    assert sanitized.debug_trace[0]["message"] == "Preview route build failed."
    assert gate._validate_public_payload(sanitized.model_dump(mode="json")) == []
