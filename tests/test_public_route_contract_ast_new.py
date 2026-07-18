from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATEWAY = "services/public_route_place_access.py"
ROUTER = "routers/user_routes.py"
LIFECYCLE = "services/user_route_state_lifecycle_service.py"
FORBIDDEN_FILTER_CALLS = {
    "apply_route_eligible_filters",
    "apply_public_place_visibility",
    "apply_public_route_eligible_filters",
    "apply_public_route_city_scope",
}


def _route_modules() -> tuple[str, ...]:
    services = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "services").rglob("*.py")
        if path.name.startswith("user_route_")
    ]
    return tuple(sorted([*services, ROUTER]))


def _tree(path: str) -> ast.AST:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _is_place_query(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "query":
        return False
    return any(isinstance(arg, ast.Name) and arg.id == "Place" for arg in node.args)


def test_public_route_modules_cannot_own_place_queries_or_partial_filters_new() -> None:
    modules = _route_modules()
    assert len(modules) >= 18
    violations: list[str] = []
    for path in modules:
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.Call):
                continue
            name = _called_name(node)
            if name in FORBIDDEN_FILTER_CALLS:
                violations.append(f"{path}:{node.lineno}: forbidden partial filter {name}()")
            if _is_place_query(node):
                violations.append(f"{path}:{node.lineno}: direct query(Place); gateway owns public route-place access")
    assert not violations, "\n".join(violations)


def test_gateway_is_only_owner_of_complete_route_scope_new() -> None:
    tree = _tree(GATEWAY)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "PublicRouteScope" in classes
    assert {
        "resolve_public_city_scope",
        "resolve_intent_scope",
        "resolve_route_scope",
        "public_route_place_query",
        "load_public_route_place",
        "load_public_route_places",
    }.issubset(functions)
    called = {_called_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert "apply_public_route_eligible_filters" in called


def test_lifecycle_facade_signs_outputs_and_verifies_every_state_operation_new() -> None:
    lifecycle_calls = {
        _called_name(node)
        for node in ast.walk(_tree(LIFECYCLE))
        if isinstance(node, ast.Call)
    }
    assert {"register_initial_route_state", "verify_current_route_state", "advance_route_state"} <= lifecycle_calls

    router_tree = _tree(ROUTER)
    functions = {node.name: node for node in router_tree.body if isinstance(node, ast.FunctionDef)}
    protected = {
        "correct_user_route": "correct",
        "update_user_route": "update_order",
        "replace_user_route_place": "replace_place",
        "read_user_route_alternatives_from_state": "read_alternatives",
        "add_user_route_place": "add_place",
        "start_user_route_session": "start_session",
    }
    violations: list[str] = []
    for function_name, required_call in protected.items():
        function_calls = {
            _called_name(node)
            for node in ast.walk(functions[function_name])
            if isinstance(node, ast.Call)
        }
        if required_call not in function_calls:
            violations.append(f"{function_name}: missing lifecycle {required_call}()")
    assert not violations, "\n".join(violations)
