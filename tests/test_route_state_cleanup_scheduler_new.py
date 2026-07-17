from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import core.route_state_cleanup_scheduler as scheduler
from services.user_route_state_registry_service import (
    ACTIVE_ROUTE_STATE_TTL,
    PREVIEW_ROUTE_STATE_TTL,
    _state_ttl,
)

ROOT = Path(__file__).resolve().parent.parent


def test_preview_states_have_shorter_ttl_than_active_states_new() -> None:
    preview = SimpleNamespace(status="preview")
    active = SimpleNamespace(status="ready")

    assert _state_ttl(preview) == PREVIEW_ROUTE_STATE_TTL
    assert _state_ttl(active) == ACTIVE_ROUTE_STATE_TTL
    assert PREVIEW_ROUTE_STATE_TTL < ACTIVE_ROUTE_STATE_TTL


def test_cleanup_scheduler_is_wired_into_application_lifespan_new() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }

    assert "start_route_state_cleanup_scheduler" in calls
    assert "stop_route_state_cleanup_scheduler" in calls


def test_cleanup_scheduler_is_bounded_and_survives_iteration_failures_new() -> None:
    source = (ROOT / "core/route_state_cleanup_scheduler.py").read_text(encoding="utf-8")

    assert "ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN" in source
    assert "ROUTE_STATE_CLEANUP_BATCH_LIMIT" in source
    assert "except Exception" in source
    assert "logger.exception" in source
    assert "not _task.done()" in source
    assert "stop_event.is_set()" in source
    assert "task.cancel()" not in source


def test_cleanup_scheduler_restarts_after_completed_task_new(monkeypatch) -> None:
    completed = SimpleNamespace(done=lambda: True)
    replacement = object()
    monkeypatch.setattr(scheduler, "_task", completed)
    monkeypatch.setattr(scheduler, "_stop_event", None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    def fake_create_task(coroutine):
        coroutine.close()
        return replacement

    monkeypatch.setattr(scheduler.asyncio, "create_task", fake_create_task)

    scheduler.start_route_state_cleanup_scheduler()

    assert scheduler._task is replacement
    assert scheduler._stop_event is not None


def test_cleanup_scheduler_continues_after_iteration_failure_new(monkeypatch) -> None:
    calls = 0

    async def fake_to_thread(_function, stop_event):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("cleanup failed")
        stop_event.set()
        return 0

    monkeypatch.setattr(scheduler.asyncio, "to_thread", fake_to_thread)

    async def exercise() -> None:
        await scheduler._scheduler_loop(asyncio.Event())

    asyncio.run(exercise())

    assert calls == 2


def test_cleanup_scheduler_shutdown_waits_for_active_batch_new(monkeypatch) -> None:
    async def exercise() -> None:
        batch_started = asyncio.Event()
        release_batch = asyncio.Event()
        stop_event = asyncio.Event()

        async def fake_to_thread(_function, _stop_event):
            batch_started.set()
            await release_batch.wait()
            return 0

        monkeypatch.setattr(scheduler.asyncio, "to_thread", fake_to_thread)
        task = asyncio.create_task(scheduler._scheduler_loop(stop_event))
        await batch_started.wait()

        stop_event.set()
        await asyncio.sleep(0)
        assert not task.done(), "shutdown must not abandon a running cleanup transaction"

        release_batch.set()
        await task

    asyncio.run(exercise())


def test_bounded_cleanup_stops_before_next_batch_after_shutdown_new(monkeypatch) -> None:
    stop_event = asyncio.Event()
    calls = 0

    def fake_run_once(*, limit):
        nonlocal calls
        calls += 1
        stop_event.set()
        return limit

    monkeypatch.setattr(scheduler, "run_route_state_cleanup_once", fake_run_once)

    deleted = scheduler._run_bounded_cleanup(stop_event)

    assert calls == 1
    assert deleted == scheduler.ROUTE_STATE_CLEANUP_BATCH_LIMIT


def test_cleanup_remains_outside_route_request_lifecycle_new() -> None:
    router_source = (ROOT / "routers/user_routes.py").read_text(encoding="utf-8")
    registry_source = (ROOT / "services/user_route_state_registry_service.py").read_text(encoding="utf-8")

    assert "cleanup_expired_route_states" not in router_source
    assert "cleanup_expired_route_states" not in registry_source
