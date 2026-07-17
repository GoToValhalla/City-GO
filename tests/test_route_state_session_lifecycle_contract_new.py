from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.route_state_cleanup_scheduler as cleanup_scheduler
import main as app_main
import services.user_route_state_lifecycle_service as lifecycle_module
from services.user_route_session_service import UserRouteSessionService
from services.user_route_state_lifecycle_service import (
    RouteStateLifecycleService,
    UserRouteStateConflictError,
)

ROOT = Path(__file__).resolve().parents[1]


def test_preview_state_cannot_start_session_new(monkeypatch) -> None:
    verified: list[tuple[object, bool]] = []
    service_called = False

    def fake_verify(_db, state, *, lock):
        verified.append((state, lock))
        return object()

    def fake_start(_self, _db, _request):
        nonlocal service_called
        service_called = True
        return object()

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    monkeypatch.setattr(UserRouteSessionService, "start", fake_start)
    state = SimpleNamespace(status="preview")
    request = SimpleNamespace(current_route=state)

    with pytest.raises(UserRouteStateConflictError):
        RouteStateLifecycleService().start_session(object(), request)

    assert verified == [(state, True)]
    assert service_called is False


def test_ready_state_starts_session_after_locked_verification_new(monkeypatch) -> None:
    sequence: list[str] = []
    expected = object()

    def fake_verify(_db, _state, *, lock):
        assert lock is True
        sequence.append("verify")
        return object()

    def fake_start(_self, _db, _request):
        sequence.append("start")
        return expected

    monkeypatch.setattr(lifecycle_module, "verify_current_route_state", fake_verify)
    monkeypatch.setattr(UserRouteSessionService, "start", fake_start)
    state = SimpleNamespace(status="ready")
    request = SimpleNamespace(current_route=state)

    result = RouteStateLifecycleService().start_session(object(), request)

    assert result is expected
    assert sequence == ["verify", "start"]


def test_lifecycle_facade_has_no_generic_verified_write_callback_new() -> None:
    service = RouteStateLifecycleService()

    assert hasattr(service, "read_alternatives")
    assert hasattr(service, "start_session")
    assert not hasattr(service, "run_verified_read")
    assert not hasattr(service, "verify")


def test_router_uses_explicit_read_and_session_contracts_new() -> None:
    source = (ROOT / "routers/user_routes.py").read_text(encoding="utf-8")

    assert "_lifecycle.read_alternatives(" in source
    assert "_lifecycle.start_session(" in source
    assert "run_verified_read" not in source
    assert "lambda: UserRouteSessionService().start" not in source


def test_session_start_service_is_only_called_by_lifecycle_owner_new() -> None:
    lifecycle_path = ROOT / "services/user_route_state_lifecycle_service.py"
    violations: list[str] = []

    for directory in (ROOT / "services", ROOT / "routers", ROOT / "core"):
        for path in directory.rglob("*.py"):
            if path == lifecycle_path:
                continue
            if "UserRouteSessionService().start(" in path.read_text(encoding="utf-8"):
                violations.append(str(path.relative_to(ROOT)))

    assert not violations, "session start bypasses lifecycle owner:\n" + "\n".join(violations)


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
