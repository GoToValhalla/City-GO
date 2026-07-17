from __future__ import annotations

import ast
from pathlib import Path

from models.user_route_state_registry import UserRouteStateRegistry

ROOT = Path(__file__).resolve().parent.parent


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found")


def _call_positions(function: ast.FunctionDef, names: set[str]) -> dict[str, int]:
    positions: dict[str, int] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        if name in names:
            positions.setdefault(name, node.lineno)
    return positions


def test_registry_cleanup_index_matches_query_order_new() -> None:
    table = UserRouteStateRegistry.__table__
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert indexes["ix_user_route_state_registry_expires_at_route_id"] == (
        "expires_at",
        "route_id",
    )
    assert "ix_user_route_state_registry_expires_at" not in indexes


def test_cleanup_index_migration_replaces_legacy_index_new() -> None:
    source = (
        ROOT / "migrations/versions/b3c4d5e6f7a8_optimize_route_state_cleanup_index.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "e7f9b2c4a6d8"' in source
    assert 'batch.drop_index(_OLD_INDEX)' in source
    assert '["expires_at", "route_id"]' in source
    assert 'batch.drop_index(_CLEANUP_INDEX)' in source
    assert '["expires_at"]' in source


def test_cleanup_owner_never_locks_public_evidence_new() -> None:
    cleanup_source = (ROOT / "services/route_state_cleanup_service.py").read_text(encoding="utf-8")

    assert "models.city" not in cleanup_source
    assert "models.place" not in cleanup_source
    assert "lock_public_route_state" not in cleanup_source
    assert "FOR UPDATE SKIP LOCKED" in cleanup_source
    assert "ORDER BY expires_at, route_id" in cleanup_source


def test_request_lock_order_is_registry_then_public_evidence_new() -> None:
    tree = ast.parse(
        (ROOT / "services/user_route_state_registry_service.py").read_text(encoding="utf-8")
    )

    register = _function(tree, "register_initial_route_state")
    register_calls = _call_positions(register, {"_locked_registry", "lock_public_route_state"})
    assert register_calls["_locked_registry"] < register_calls["lock_public_route_state"]

    verify = _function(tree, "verify_current_route_state")
    verify_calls = _call_positions(verify, {"with_for_update", "lock_public_route_state"})
    assert verify_calls["with_for_update"] < verify_calls["lock_public_route_state"]


def test_registry_service_is_only_runtime_expiry_writer_new() -> None:
    violations: list[str] = []
    allowed = ROOT / "services/user_route_state_registry_service.py"

    for directory in (ROOT / "services", ROOT / "routers", ROOT / "core"):
        for path in directory.rglob("*.py"):
            if path == allowed:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                targets: list[ast.expr] = []
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    if isinstance(node, ast.Assign):
                        targets.extend(node.targets)
                    else:
                        targets.append(node.target)
                elif isinstance(node, ast.AugAssign):
                    targets.append(node.target)
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr == "expires_at":
                        violations.append(f"{path.relative_to(ROOT)}:{target.lineno}")

    assert not violations, "registry expiry must have one runtime writer:\n" + "\n".join(violations)
