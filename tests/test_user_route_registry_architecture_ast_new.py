from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTER = ROOT / "routers/user_routes.py"
LIFECYCLE = ROOT / "services/user_route_state_lifecycle_service.py"
REGISTRY = ROOT / "services/user_route_state_registry_service.py"
SESSION = ROOT / "services/user_route_session_service.py"
INTEGRITY = ROOT / "services/user_route_state_integrity.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(_source(path), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            result.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            result.add(node.func.attr)
    return result


def test_user_route_router_delegates_complete_registry_lifecycle_new() -> None:
    router_calls = _called_names(ROUTER)
    lifecycle_calls = _called_names(LIFECYCLE)
    assert {"issue_initial", "correct", "update_order", "replace_place", "add_place", "read_alternatives", "start_session"} <= router_calls
    assert {"register_initial_route_state", "verify_current_route_state", "advance_route_state"} <= lifecycle_calls


def test_registry_uses_atomic_missing_row_claim_new() -> None:
    source = _source(REGISTRY)
    assert "on_conflict_do_nothing" in source
    assert "with_for_update" in source
    assert "db.rollback" not in source
    assert "db.commit" not in source


def test_session_service_never_owns_outer_transaction_new() -> None:
    source = _source(SESSION)
    assert "db.commit" not in source
    assert "db.rollback" not in source
    assert "begin_nested" in source


def test_session_actions_are_row_locked_new() -> None:
    tree = ast.parse(_source(SESSION), filename=str(SESSION))
    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "apply_action"
    )
    calls = {
        node.func.attr
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "with_for_update" in calls


def test_runtime_startup_requires_route_state_secret_without_trusting_app_env_new() -> None:
    main_source = _source(ROOT / "main.py")
    integrity_source = _source(INTEGRITY)
    assert "validate_route_state_runtime_config" in main_source
    assert "USER_ROUTE_STATE_SECRET" in integrity_source
    assert "user_route_state_secret" in integrity_source
    validator = integrity_source.split("def validate_route_state_runtime_config", 1)[1].split("def _canonical_payload", 1)[0]
    assert "_is_production" not in validator
