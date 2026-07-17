from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_CALLS = {
    "apply_route_eligible_filters",
    "apply_public_place_visibility",
    "apply_public_route_eligible_filters",
}
ALLOWED_GATEWAY = "services/public_route_place_access.py"


def _public_route_modules() -> tuple[str, ...]:
    return tuple(
        sorted(
            str(path.relative_to(ROOT))
            for path in (ROOT / "services").rglob("*.py")
            if path.name.startswith("user_route_")
        )
    )


def _called_names(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def test_public_route_modules_cannot_apply_incomplete_filters_directly_new() -> None:
    modules = _public_route_modules()
    assert len(modules) > 20
    violations: list[str] = []
    for path in modules:
        called = _called_names(path)
        forbidden = sorted(called & FORBIDDEN_CALLS)
        if forbidden:
            violations.append(f"{path}: direct incomplete filter calls {forbidden}; use public_route_place_access")
    assert not violations, "\n".join(violations)


def test_public_route_gateway_owns_complete_scope_composition_new() -> None:
    source = (ROOT / ALLOWED_GATEWAY).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "apply_public_route_eligible_filters" in called
    assert "resolve_route_city_id" in {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "apply_public_route_city_scope" in {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_no_route_module_compares_place_city_fk_to_context_city_id_new() -> None:
    violations: list[str] = []
    for path in _public_route_modules():
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            text = ast.unparse(node)
            if "Place.city_id" in text and ".context.city_id" in text:
                violations.append(f"{path}:{node.lineno}: {text}")
    assert not violations, "slug-valued context.city_id compared to integer Place.city_id:\n" + "\n".join(violations)
