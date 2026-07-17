from __future__ import annotations

from types import SimpleNamespace

import pytest

import services.user_route_state_lifecycle_service as lifecycle_module
from services.user_route_session_service import UserRouteSessionService
from services.user_route_state_lifecycle_service import (
    RouteStateLifecycleService,
    UserRouteStateConflictError,
)


@pytest.mark.parametrize("status", ["ready", "partial_route", "corrected"])
def test_usable_route_status_can_start_session_new(monkeypatch, status: str) -> None:
    expected = object()
    calls: list[str] = []

    def fake_verify(_db, _state, *, lock):
        assert lock is True
        calls.append("verify")
        return object()

    def fake_start(_self, _db, _request):
        calls.append("start")
        return expected

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    monkeypatch.setattr(UserRouteSessionService, "start", fake_start)
    request = SimpleNamespace(current_route=SimpleNamespace(status=status))

    assert RouteStateLifecycleService().start_session(object(), request) is expected
    assert calls == ["verify", "start"]


@pytest.mark.parametrize("status", ["preview", "preview_failed"])
def test_preview_status_cannot_start_session_new(monkeypatch, status: str) -> None:
    service_called = False

    def fake_verify(_db, _state, *, lock):
        assert lock is True
        return object()

    def fake_start(_self, _db, _request):
        nonlocal service_called
        service_called = True
        return object()

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    monkeypatch.setattr(UserRouteSessionService, "start", fake_start)
    request = SimpleNamespace(current_route=SimpleNamespace(status=status))

    with pytest.raises(UserRouteStateConflictError):
        RouteStateLifecycleService().start_session(object(), request)
    assert service_called is False
