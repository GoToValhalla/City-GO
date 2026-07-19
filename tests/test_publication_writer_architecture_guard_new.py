from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.publication_state_ownership import (
    CONTROLLED_PLACE_INPUT_FIELDS,
    PUBLICATION_OWNED_FIELDS,
    VERIFICATION_OWNED_FIELDS,
)
from services.place_change_review_service import RESTORABLE_PLACE_FIELDS
from services.place_service import PROTECTED_CONTROLLED_FIELDS
from tests.allure_support import title

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = (
    ROOT / "services",
    ROOT / "routers",
    ROOT / "scripts",
    ROOT / "data" / "scripts",
    ROOT / "telegram_bot",
)
PUBLICATION_WRITER = (ROOT / "services" / "publication_state_writer.py").resolve()
VERIFICATION_WRITER = (ROOT / "services" / "place_verification_mutation.py").resolve()
APPROVED_DYNAMIC_SETATTR = {
    (ROOT / "services" / "admin_place_update_service.py").resolve(),
    (ROOT / "services" / "place_service.py").resolve(),
    (ROOT / "services" / "place_change_review_service.py").resolve(),
}


def _python_files() -> list[Path]:
    result: list[Path] = []
    for root in PRODUCTION_ROOTS:
        if root.exists():
            result.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(set(result))


def _annotation_mentions_place(node: ast.AST | None) -> bool:
    return node is not None and any(
        isinstance(child, ast.Name) and child.id == "Place" for child in ast.walk(node)
    )


def _place_names(tree: ast.AST) -> set[str]:
    names = {"place", "locked_place"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if _annotation_mentions_place(arg.annotation):
                    names.add(arg.arg)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            constructor = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "Place"
            )
            annotated = isinstance(node, ast.AnnAssign) and _annotation_mentions_place(node.annotation)
            if constructor or annotated:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def _receiver_is_place(node: ast.AST, place_names: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Place" or node.id in place_names
    if isinstance(node, ast.Attribute):
        return _receiver_is_place(node.value, place_names) or node.attr in place_names
    if isinstance(node, ast.Subscript):
        return _receiver_is_place(node.value, place_names)
    return False


def _assignment_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def _flatten_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, (ast.Tuple, ast.List)):
        return [child for item in node.elts for child in _flatten_targets(item)]
    return [node]


def _owner_for(field: str) -> Path | None:
    if field in PUBLICATION_OWNED_FIELDS:
        return PUBLICATION_WRITER
    if field in VERIFICATION_OWNED_FIELDS:
        return VERIFICATION_WRITER
    return None


def _violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    place_names = _place_names(tree)
    violations: list[str] = []

    def forbidden(field: object) -> bool:
        return isinstance(field, str) and _owner_for(field) not in {None, path.resolve()}

    for node in ast.walk(tree):
        for target in _assignment_targets(node):
            for flattened in _flatten_targets(target):
                if (
                    isinstance(flattened, ast.Attribute)
                    and forbidden(flattened.attr)
                    and _receiver_is_place(flattened.value, place_names)
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: direct controlled Place assignment to {flattened.attr}"
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr":
            if len(node.args) < 2:
                continue
            receiver, field_node = node.args[0], node.args[1]
            if isinstance(field_node, ast.Constant):
                if forbidden(field_node.value) and _receiver_is_place(receiver, place_names):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: controlled Place setattr bypass for {field_node.value}"
                    )
            elif _receiver_is_place(receiver, place_names) and path.resolve() not in APPROVED_DYNAMIC_SETATTR:
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: unbounded dynamic Place setattr"
                )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr not in {"update", "values"} or "Place" not in ast.unparse(node.func.value):
                continue
            fields: list[object] = [keyword.arg for keyword in node.keywords]
            for argument in node.args:
                if isinstance(argument, ast.Dict):
                    fields.extend(key.value for key in argument.keys if isinstance(key, ast.Constant))
            for field in fields:
                if forbidden(field):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: controlled Place bulk bypass for {field}"
                    )

    normalized = " ".join(text.lower().split())
    if "update places" in normalized and path.resolve() not in {PUBLICATION_WRITER, VERIFICATION_WRITER}:
        violations.append(f"{path.relative_to(ROOT)}: raw UPDATE places statement")
    return violations


@title("Only canonical owners may mutate controlled Place state")
def test_no_controlled_place_state_mutation_bypasses() -> None:
    violations = [violation for path in _python_files() for violation in _violations(path)]
    assert violations == [], "Controlled Place state bypasses found:\n" + "\n".join(violations)


def test_dynamic_boundaries_share_complete_registry() -> None:
    assert PROTECTED_CONTROLLED_FIELDS == CONTROLLED_PLACE_INPUT_FIELDS
    assert RESTORABLE_PLACE_FIELDS.isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)


def test_guard_distinguishes_place_from_other_models() -> None:
    tree = ast.parse(
        """
def mutate(place: Place, category: Category, route: Route):
    place.is_route_eligible = False
    place.verification_status = 'verified'
    category.is_route_eligible = False
    category.is_searchable = False
    route.is_active = False
"""
    )
    names = _place_names(tree)
    protected = [
        target.attr
        for node in ast.walk(tree)
        for target in _assignment_targets(node)
        if isinstance(target, ast.Attribute)
        and target.attr in CONTROLLED_PLACE_INPUT_FIELDS
        and _receiver_is_place(target.value, names)
    ]
    assert protected == ["is_route_eligible", "verification_status"]


@pytest.mark.parametrize("field", sorted(CONTROLLED_PLACE_INPUT_FIELDS))
def test_owner_registry_covers_every_controlled_field(field: str) -> None:
    assert _owner_for(field) is not None or field not in (
        PUBLICATION_OWNED_FIELDS | VERIFICATION_OWNED_FIELDS
    )
