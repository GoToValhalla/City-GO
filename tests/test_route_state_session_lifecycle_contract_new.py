from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import core.route_state_cleanup_scheduler as cleanup_scheduler
import main as app_main
import services.user_route_state_lifecycle_service as lifecycle_module
from services.user_route_state_lifecycle_service import (
    RouteStateLifecycleService,
    UserRouteStateConflictError,
)


def test_preview_state_cannot_start_session_new(monkeypatch) -> None:
    verified: list[tuple[object, bool]] = []
    operation_called = False

    def fake_verify(_db, state, *, lock):
        verified.append((state, lock))
        return object()

    def operation():
        nonlocal operation_called
        operation_called = True
        return object()

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    state = SimpleNamespace(status="preview")

    with pytest.raises(UserRouteStateConflictError):
        RouteStateLifecycleService().start_session(object(), state, operation)

    assert verified == [(state, True)]
    assert operation_called is False


def test_ready_state_starts_session_after_locked_verification_new(monkeypatch) -> None:
    sequence: list[str] = []
    expected = object()

    def fake_verify(_db, _state, *, lock):
        assert lock is True
        sequence.append("verify")
        return object()

    def operation():
        sequence.append("start")
        return expected

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    state = SimpleNamespace(status="ready")

    result = RouteStateLifecycleService().start_session(object(), state, operation)

    assert result is expected
    assert sequence == ["verify", "start"]


def test_lifecycle_facade_has_no_generic_verified_write_callback_new() -> None:
    service = RouteStateLifecycleService()

    assert hasattr(service, "read_alternatives")
    assert hasattr(service, "start_session")
    assert not hasattr(service, "run_verified_read")


def test_router_uses_explicit_read_and_session_contracts_new() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "routers/user_routes.py").read_text(encoding="utf-8")

    assert "_lifecycle.read_alternatives(" in source
    assert "_lifecycle.start_session(" in source
    assert "run_verified_read" not in source


def test_owned_scheduler_external_cancellation_is_normalized_after_drain_new(monkeypatch) -> None:
    async def exercise() -> None:
        task = asyncio.create_task(asyncio.sleep(60))
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        monkeypatch.setattr(cleanup_scheduler, "_task", task)
        monkeypatch.setattr(cleanup_scheduler, "_wake_event", asyncio.Event())
        monkeypatch.setattr(cleanup_scheduler, "_thread_stop_event", cleanup_scheduler.ThreadEvent())
        monkeypatch.setattr(cleanup_scheduler, "_active_batch", None)

        await cleanup_scheduler.stop_route_state_cleanup_scheduler()

        assert cleanup_scheduler._task is None
        assert cleanup_scheduler._wake_event is None
        assert cleanup_scheduler._thread_stop_event is None

    asyncio.run(exercise())


def test_shutdown_coordinator_stops_all_schedulers_when_first_stop_fails_new(monkeypatch) -> None:
    calls: list[str] = []

    async def stop_route():
        calls.append("route")
        raise RuntimeError("route stop failed")

    async def stop_import():
        calls.append("import")

    async def stop_verification():
        calls.append("verification")

    monkeypatch.setattr(app_main, "stop_route_state_cleanup_scheduler", stop_route)
    monkeypatch.setattr(app_main, "stop_import_worker_scheduler", stop_import)
    monkeypatch.setattr(app_main, "stop_place_verification_scheduler", stop_verification)

    with pytest.raises(RuntimeError, match="route stop failed"):
        asyncio.run(app_main._stop_schedulers())

    assert calls == ["route", "import", "verification"]
