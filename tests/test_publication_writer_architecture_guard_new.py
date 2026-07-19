from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.publication_state_ownership import PUBLICATION_OWNED_FIELDS
from services.place_change_review_service import PROTECTED_PUBLICATION_FIELDS as REVIEW_PROTECTED_FIELDS
from services.place_service import PROTECTED_PUBLICATION_FIELDS
from tests.allure_support import title

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = (
    ROOT / "services",
    ROOT / "routers",
    ROOT / "scripts",
    ROOT / "data" / "scripts",
    ROOT / "telegram_bot",
)
CANONICAL_WRITER = (ROOT / "services" / "publication_state_writer.py").resolve()
APPROVED_DYNAMIC_SETATTR = {
    (ROOT / "services" / "admin_place_update_service.py").resolve(),
    (ROOT / "services" / "place_service.py").resolve(),
    (ROOT / "services" / "place_change_review_service.py").resolve(),
}
PUBLICATION_FIELDS = PUBLICATION_OWNED_FIELDS


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
            is_place_constructor = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "Place"
            )
            annotated_place = isinstance(node, ast.AnnAssign) and _annotation_mentions_place(node.annotation)
            if is_place_constructor or annotated_place:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
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


def _violations(path: Path) -> list[str]:
    if path.resolve() == CANONICAL_WRITER:
        return []
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    place_names = _place_names(tree)
    violations: list[str] = []

    for node in ast.walk(tree):
        for target in _assignment_targets(node):
            for flattened in _flatten_targets(target):
                if (
                    isinstance(flattened, ast.Attribute)
                    and flattened.attr in PUBLICATION_FIELDS
                    and _receiver_is_place(flattened.value, place_names)
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: direct Place assignment to {flattened.attr}"
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr":
            if len(node.args) < 2:
                continue
            receiver, field_node = node.args[0], node.args[1]
            if isinstance(field_node, ast.Constant):
                if (
                    field_node.value in PUBLICATION_FIELDS
                    and _receiver_is_place(receiver, place_names)
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: setattr Place bypass for {field_node.value}"
                    )
            elif _receiver_is_place(receiver, place_names) and path.resolve() not in APPROVED_DYNAMIC_SETATTR:
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: unbounded dynamic Place setattr"
                )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"update", "values"}:
                call_text = ast.unparse(node.func.value)
                if "Place" not in call_text:
                    continue
                for keyword in node.keywords:
                    if keyword.arg in PUBLICATION_FIELDS:
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: Place bulk update bypass for {keyword.arg}"
                        )
                for argument in node.args:
                    if isinstance(argument, ast.Dict):
                        for key in argument.keys:
                            if isinstance(key, ast.Constant) and key.value in PUBLICATION_FIELDS:
                                violations.append(
                                    f"{path.relative_to(ROOT)}:{node.lineno}: Place mapping update bypass for {key.value}"
                                )

    normalized = " ".join(text.lower().split())
    if "update places" in normalized:
        violations.append(f"{path.relative_to(ROOT)}: raw UPDATE places statement")
    return violations


@title("Only canonical writer may mutate Place publication state")
def test_no_publication_state_mutation_bypasses() -> None:
    violations = [violation for path in _python_files() for violation in _violations(path)]
    assert violations == [], "Publication writer bypasses found:\n" + "\n".join(violations)


@title("Dynamic boundaries share the canonical ownership registry")
def test_dynamic_boundaries_share_canonical_registry() -> None:
    assert PROTECTED_PUBLICATION_FIELDS == PUBLICATION_OWNED_FIELDS
    assert REVIEW_PROTECTED_FIELDS == PUBLICATION_OWNED_FIELDS


def test_guard_distinguishes_place_from_category_and_route_fields() -> None:
    tree = ast.parse(
        """
def mutate(place: Place, category: Category, route: Route):
    place.is_route_eligible = False
    category.is_route_eligible = False
    category.is_searchable = False
    route.is_active = False
"""
    )
    names = _place_names(tree)
    assignments = [
        target
        for node in ast.walk(tree)
        for target in _assignment_targets(node)
        if isinstance(target, ast.Attribute)
    ]
    protected = [
        item.attr for item in assignments
        if item.attr in PUBLICATION_FIELDS and _receiver_is_place(item.value, names)
    ]
    assert protected == ["is_route_eligible"]


@pytest.mark.parametrize("field", sorted(PUBLICATION_FIELDS))
@title("Architecture guard recognizes every protected publication field")
def test_publication_guard_field_registry_is_complete(field: str) -> None:
    assert field in PUBLICATION_OWNED_FIELDS
