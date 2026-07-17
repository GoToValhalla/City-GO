from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATEWAY = "services/public_route_place_access.py"
ROUTER = "routers/user_routes.py"
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
    assert len(modules) > 20
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
    called = {
        _called_name(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "apply_public_route_eligible_filters" in called


def test_router_signs_outputs_and_verifies_every_state_mutation_new() -> None:
    source = (ROOT / ROUTER).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=ROUTER)
    called = {
        _called_name(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "sign_user_route_state" in called
    assert "verify_user_route_state" in called

    protected = {
        "correct_user_route": "_verify_current_route",
        "update_user_route": "_ensure_current_route_matches",
        "replace_user_route_place": "_ensure_current_route_matches",
        "read_user_route_alternatives_from_state": "_ensure_current_route_matches",
        "add_user_route_place": "_ensure_current_route_matches",
        "start_user_route_session": "_ensure_current_route_matches",
    }
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    violations: list[str] = []
    for function_name, required_call in protected.items():
        function = functions[function_name]
        function_calls = {
            _called_name(node)
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
        }
        if required_call not in function_calls:
            violations.append(f"{function_name}: missing {required_call}()")
    assert not violations, "\n".join(violations)
