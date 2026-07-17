from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_ROUTE_MODULES = (
    "services/user_route_edit_service.py",
    "services/user_route_place_loader.py",
    "services/user_route_slot_build_service.py",
    "services/user_route_replacement_loader.py",
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


def test_public_route_modules_use_complete_public_contract_new() -> None:
    violations: list[str] = []
    for path in PUBLIC_ROUTE_MODULES:
        called = _called_names(path)
        if "apply_route_eligible_filters" in called:
            violations.append(f"{path}: incomplete place-only route filter")
        if "apply_public_place_visibility" in called:
            violations.append(f"{path}: catalog-only public filter")
        if "apply_public_route_eligible_filters" not in called:
            violations.append(f"{path}: canonical public route contract missing")
    assert not violations, "\n".join(violations)


def test_public_route_contract_composes_publication_and_eligibility_new() -> None:
    source = (ROOT / "services/route_eligibility/query_filters.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "public_route_eligible_sql_conditions"
    )
    called = {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "public_place_conditions" in called
    assert "route_eligible_sql_conditions" in called
