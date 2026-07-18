from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import inspect

from models.user_route_state_registry import UserRouteStateRegistry

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_SERVICE = ROOT / "services/user_route_state_registry_service.py"
LIFECYCLE_SERVICE = ROOT / "services/user_route_state_lifecycle_service.py"
CLEANUP_SERVICE = ROOT / "services/route_state_cleanup_service.py"
PUBLIC_ACCESS_SERVICE = ROOT / "services/public_route_place_access.py"
ADMIN_PUBLICATION_SERVICE = ROOT / "services/admin_city_publication_service.py"
ROUTER = ROOT / "routers/user_routes.py"
ANALYTICS_SERVICE = ROOT / "services/route_analytics_service.py"


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


def _runtime_python_files():
    for directory in (ROOT / "services", ROOT / "routers", ROOT / "core"):
        yield from directory.rglob("*.py")


def test_registry_cleanup_index_matches_query_order_new() -> None:
    table = UserRouteStateRegistry.__table__
    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}
    assert indexes["ix_user_route_state_registry_expires_at_route_id"] == ("expires_at", "route_id")
    assert "ix_user_route_state_registry_expires_at" not in indexes


def test_database_schema_has_cleanup_index_new(db_session) -> None:
    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspect(db_session.get_bind()).get_indexes("user_route_state_registry")
    }
    assert indexes["ix_user_route_state_registry_expires_at_route_id"] == ("expires_at", "route_id")
    assert "ix_user_route_state_registry_expires_at" not in indexes


def test_cleanup_index_migration_replaces_legacy_index_new() -> None:
    source = (ROOT / "migrations/versions/6b9c1e4a8d3f_optimize_route_state_cleanup_index.py").read_text(encoding="utf-8")
    assert 'down_revision = "5a8b0d3f7c2e"' in source
    assert "batch.drop_index(_OLD_INDEX)" in source
    assert '["expires_at", "route_id"]' in source
    assert "batch.drop_index(_CLEANUP_INDEX)" in source
    assert '["expires_at"]' in source


def test_cleanup_owner_never_locks_public_evidence_new() -> None:
    cleanup_source = CLEANUP_SERVICE.read_text(encoding="utf-8")
    assert "models.city" not in cleanup_source
    assert "models.place" not in cleanup_source
    assert "lock_public_route_state" not in cleanup_source
    assert "FOR UPDATE SKIP LOCKED" in cleanup_source
    assert "ORDER BY expires_at, route_id" in cleanup_source


def test_request_lock_order_is_registry_then_public_evidence_new() -> None:
    tree = ast.parse(REGISTRY_SERVICE.read_text(encoding="utf-8"))
    register = _function(tree, "register_initial_route_state")
    register_calls = _call_positions(register, {"_locked_registry", "lock_public_route_state"})
    assert register_calls["_locked_registry"] < register_calls["lock_public_route_state"]
    verify = _function(tree, "verify_current_route_state")
    verify_calls = _call_positions(verify, {"with_for_update", "lock_public_route_state"})
    assert verify_calls["with_for_update"] < verify_calls["lock_public_route_state"]


def test_public_evidence_readers_use_shared_locks_new() -> None:
    source = PUBLIC_ACCESS_SERVICE.read_text(encoding="utf-8")
    assert source.count("with_for_update(read=True)") >= 3
    assert ".with_for_update()" not in source
    assert ".order_by(Place.id.asc())" in source


def test_admin_publication_writers_lock_city_then_ordered_places_new() -> None:
    source = ADMIN_PUBLICATION_SERVICE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for function_name in ("publish_city", "unpublish_city"):
        function = _function(tree, function_name)
        text = ast.get_source_segment(source, function) or ""
        city_lock = text.find("db.query(City)")
        place_lock = text.find("db.query(Place)")
        assert city_lock >= 0
        assert place_lock > city_lock
        assert ".order_by(Place.id.asc())" in text
        assert text.count(".with_for_update()") >= 2


def test_router_uses_only_public_lifecycle_facade_new() -> None:
    source = ROUTER.read_text(encoding="utf-8")
    assert "user_route_state_lifecycle_service" in source
    assert "user_route_state_registry_service" not in source
    assert "register_initial_route_state" not in source
    assert "verify_current_route_state" not in source
    assert "advance_route_state" not in source


def test_only_lifecycle_facade_imports_registry_primitives_new() -> None:
    violations: list[str] = []
    primitive_names = {"register_initial_route_state", "verify_current_route_state", "advance_route_state"}
    for path in _runtime_python_files():
        if path in {REGISTRY_SERVICE, LIFECYCLE_SERVICE}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and {alias.name for alias in node.names} & primitive_names:
                violations.append(str(path.relative_to(ROOT)))
    assert not violations, "registry primitives escaped lifecycle facade:\n" + "\n".join(violations)


def test_registry_service_is_only_runtime_orm_owner_new() -> None:
    violations = [
        str(path.relative_to(ROOT))
        for path in _runtime_python_files()
        if path != REGISTRY_SERVICE and "UserRouteStateRegistry" in path.read_text(encoding="utf-8")
    ]
    assert not violations, "route-state registry ORM ownership escaped the registry service:\n" + "\n".join(violations)


def test_no_raw_registry_write_bypasses_lifecycle_owners_new() -> None:
    violations: list[str] = []
    for path in _runtime_python_files():
        normalized = " ".join(path.read_text(encoding="utf-8").lower().split())
        if "update user_route_state_registry" in normalized:
            violations.append(f"{path.relative_to(ROOT)}:UPDATE")
        if "insert into user_route_state_registry" in normalized:
            violations.append(f"{path.relative_to(ROOT)}:INSERT")
        if "delete from user_route_state_registry" in normalized and path != CLEANUP_SERVICE:
            violations.append(f"{path.relative_to(ROOT)}:DELETE")
    assert not violations, "raw registry writes bypass lifecycle ownership:\n" + "\n".join(violations)


def test_database_errors_are_not_domain_conflicts_new() -> None:
    source = ROUTER.read_text(encoding="utf-8")
    assert "_ROUTE_STATE_ERRORS = (UserRouteStateConflictError, UserRouteStateIntegrityError)" in source
    assert "status_code=503" in source
    assert "route_state_database_unavailable" in source


def test_route_analytics_uses_isolated_session_new() -> None:
    source = ANALYTICS_SERVICE.read_text(encoding="utf-8")
    assert "SessionLocal()" in source
    assert "caller Session is deliberately ignored" in source
    assert "db.close()" in source


def test_user_route_state_services_do_not_commit_or_rollback_request_session_new() -> None:
    violations: list[str] = []
    for path in (ROOT / "services").glob("user_route_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"commit", "rollback"}:
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.func.attr}")
    assert not violations, "user route-state service owns caller transaction:\n" + "\n".join(violations)
