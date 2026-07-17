from __future__ import annotations

import asyncio
import ast
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
LIFECYCLE_PATH = ROOT / "services/user_route_state_lifecycle_service.py"
ROUTER_PATH = ROOT / "routers/user_routes.py"
SCHEDULER_PATH = ROOT / "core/route_state_cleanup_scheduler.py"


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


def test_lifecycle_facade_exposes_only_concrete_public_operations_new() -> None:
    service = RouteStateLifecycleService()

    for operation in (
        "issue_initial",
        "correct",
        "update_order",
        "replace_place",
        "add_place",
        "read_alternatives",
        "start_session",
    ):
        assert hasattr(service, operation)
    for forbidden in ("mutate", "verify", "run_verified_read"):
        assert not hasattr(service, forbidden)


def test_lifecycle_facade_accepts_no_callable_contract_new() -> None:
    source = LIFECYCLE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "collections.abc import Callable" not in source
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assert all(
            not (isinstance(argument.annotation, ast.Name) and argument.annotation.id == "Callable")
            for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        )


def test_router_uses_only_concrete_lifecycle_mutations_new() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")

    for operation in ("correct", "update_order", "replace_place", "add_place"):
        assert f"_lifecycle.{operation}(" in source
    assert "_lifecycle.mutate(" not in source
    assert "_mutate_route_state" not in source
    assert "lambda:" not in source


def test_session_start_service_is_only_called_by_lifecycle_owner_new() -> None:
    violations: list[str] = []

    for directory in (ROOT / "services", ROOT / "routers", ROOT / "core"):
        for path in directory.rglob("*.py"):
            if path == LIFECYCLE_PATH:
                continue
            if "UserRouteSessionService().start(" in path.read_text(encoding="utf-8"):
                violations.append(str(path.relative_to(ROOT)))

    assert not violations, "session start bypasses lifecycle owner:\n" + "\n".join(violations)


def test_scheduler_ownership_is_finalized_only_by_done_callback_new() -> None:
    source = SCHEDULER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    stop = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "stop_route_state_cleanup_scheduler")
    finalize = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_finalize_scheduler_ownership")
    stop_source = ast.get_source_segment(source, stop) or ""
    finalize_source = ast.get_source_segment(source, finalize) or ""

    assert "add_done_callback(_finalize_scheduler_ownership)" in source
    assert "_task = None" not in stop_source
    assert "_wake_event = None" not in stop_source
    assert "_thread_stop_event = None" not in stop_source
    assert "_task = None" in finalize_source
    assert "_state = \"stopped\"" in finalize_source


def test_cancelled_stop_retains_ownership_until_scheduler_task_done_new(monkeypatch) -> None:
    async def exercise() -> None:
        release = asyncio.Event()

        async def owned_scheduler() -> None:
            await release.wait()

        task = asyncio.create_task(owned_scheduler())
        task.add_done_callback(cleanup_scheduler._finalize_scheduler_ownership)
        monkeypatch.setattr(cleanup_scheduler, "_task", task)
        monkeypatch.setattr(cleanup_scheduler, "_state", "running")
        monkeypatch.setattr(cleanup_scheduler, "_wake_event", asyncio.Event())
        monkeypatch.setattr(cleanup_scheduler, "_thread_stop_event", cleanup_scheduler.ThreadEvent())
        monkeypatch.setattr(cleanup_scheduler, "_active_batch", None)

        stop_task = asyncio.create_task(cleanup_scheduler.stop_route_state_cleanup_scheduler())
        await asyncio.sleep(0)
        stop_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stop_task

        assert cleanup_scheduler._task is task
        assert cleanup_scheduler._state == "stopping"

        release.set()
        await task
        await asyncio.sleep(0)

        assert cleanup_scheduler._task is None
        assert cleanup_scheduler._state == "stopped"

    asyncio.run(exercise())


def test_owned_scheduler_external_cancellation_is_normalized_after_drain_new(monkeypatch) -> None:
    async def exercise() -> None:
        task = asyncio.create_task(asyncio.sleep(60))
        monkeypatch.setattr(cleanup_scheduler, "_task", task)
        monkeypatch.setattr(cleanup_scheduler, "_state", "running")
        monkeypatch.setattr(cleanup_scheduler, "_wake_event", asyncio.Event())
        monkeypatch.setattr(cleanup_scheduler, "_thread_stop_event", cleanup_scheduler.ThreadEvent())
        monkeypatch.setattr(cleanup_scheduler, "_active_batch", None)
        task.add_done_callback(cleanup_scheduler._finalize_scheduler_ownership)
        task.cancel()

        await cleanup_scheduler.stop_route_state_cleanup_scheduler()
        await asyncio.sleep(0)

        assert cleanup_scheduler._task is None
        assert cleanup_scheduler._state == "stopped"

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
