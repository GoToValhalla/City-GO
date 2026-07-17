from __future__ import annotations

import ast
from pathlib import Path

from schemas.user_route import UserRouteState
from services.user_route_state_registry_service import (
    ACTIVE_ROUTE_STATE_TTL,
    PREVIEW_ROUTE_STATE_TTL,
    _state_ttl,
)

ROOT = Path(__file__).resolve().parent.parent


def test_preview_states_have_shorter_ttl_than_active_states_new() -> None:
    preview = UserRouteState(route_id="preview", status="preview")
    active = UserRouteState(route_id="active", status="ready")

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


def test_cleanup_remains_outside_route_request_lifecycle_new() -> None:
    router_source = (ROOT / "routers/user_routes.py").read_text(encoding="utf-8")
    registry_source = (ROOT / "services/user_route_state_registry_service.py").read_text(encoding="utf-8")

    assert "cleanup_expired_route_states" not in router_source
    assert "cleanup_expired_route_states" not in registry_source
