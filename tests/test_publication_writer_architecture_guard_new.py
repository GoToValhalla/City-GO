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
PUBLICATION_WRITER = (ROOT / "services" / "publication_state_writer.py").resolve()
VERIFICATION_WRITER = (ROOT / "services" / "place_verification_mutation.py").resolve()
IMPORT_LIFECYCLE = (ROOT / "services" / "place_import_lifecycle_service.py").resolve()
APPROVED_DYNAMIC_SETATTR = {
    (ROOT / "services" / "admin_place_update_service.py").resolve(),
    (ROOT / "services" / "place_service.py").resolve(),
    (ROOT / "services" / "place_change_review_service.py").resolve(),
    IMPORT_LIFECYCLE,
}
EXCLUDED_PATH_PARTS = {
    ".git", ".venv", "venv", "node_modules", "frontend", "tests",
    "migrations", "alembic", "__pycache__",
}
SHARED_MODEL_FIELDS = frozenset({"is_active", "is_searchable", "is_route_eligible"})
NON_PLACE_MODEL_NAMES = frozenset({"City", "Route", "Category", "Tag", "Collection", "Destination"})


def _python_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if not any(part in EXCLUDED_PATH_PARTS for part in path.relative_to(ROOT).parts)
    )


def _annotation_mentions(node: ast.AST | None, name: str) -> bool:
    return node is not None and any(
        isinstance(child, ast.Name) and child.id == name for child in ast.walk(node)
    )


def _target_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _typed_names(tree: ast.AST, model_name: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if _annotation_mentions(arg.annotation, model_name):
                    names.add(arg.arg)
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        value_text = ast.unparse(value) if value is not None else ""
        constructor = (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == model_name
        )
        query_result = model_name in value_text and any(
            token in value_text
            for token in ("query(", "get(", "select(", ".one(", ".first(", ".one_or_none(")
        )
        annotated = isinstance(node, ast.AnnAssign) and _annotation_mentions(node.annotation, model_name)
        place_container_item = (
            model_name == "Place"
            and isinstance(value, ast.Subscript)
            and "place" in ast.unparse(value.value).lower()
        )
        if constructor or query_result or annotated or place_container_item:
            names.update(_target_names(node))

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            if _receiver_name(node.value) in names:
                before = len(names)
                names.update(_target_names(node))
                changed = changed or len(names) != before
    return names


def _receiver_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _receiver_name(node.value)
    if isinstance(node, ast.Subscript):
        return _receiver_name(node.value)
    return None


def _receiver_is_place(node: ast.AST, place_names: set[str], non_place_names: set[str]) -> bool:
    name = _receiver_name(node)
    if name in non_place_names:
        return False
    if name == "Place" or name in place_names:
        return True
    if isinstance(node, ast.Attribute) and node.attr in place_names:
        return True
    if isinstance(node, ast.Subscript):
        return "place" in ast.unparse(node.value).lower()
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


def _field_targets_place(
    field: str,
    receiver: ast.AST,
    place_names: set[str],
    non_place_names: set[str],
) -> bool:
    if field not in SHARED_MODEL_FIELDS:
        return _receiver_name(receiver) not in non_place_names
    return _receiver_is_place(receiver, place_names, non_place_names)


def _violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    place_names = {"place", "locked_place"} | _typed_names(tree, "Place")
    non_place_names = set().union(*(_typed_names(tree, name) for name in NON_PLACE_MODEL_NAMES))
    violations: list[str] = []

    def forbidden(field: object) -> bool:
        return isinstance(field, str) and _owner_for(field) not in {None, path.resolve()}

    for node in ast.walk(tree):
        for target in _assignment_targets(node):
            for flattened in _flatten_targets(target):
                if (
                    isinstance(flattened, ast.Attribute)
                    and forbidden(flattened.attr)
                    and _field_targets_place(flattened.attr, flattened.value, place_names, non_place_names)
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: direct controlled Place assignment to {flattened.attr}"
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_set_if_changed" and path.resolve() == IMPORT_LIFECYCLE:
                if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: import mutation field must be a literal"
                    )
                elif forbidden(node.args[1].value):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: import helper bypass for {node.args[1].value}"
                    )

            if node.func.id == "setattr":
                if len(node.args) < 2:
                    continue
                receiver, field_node = node.args[0], node.args[1]
                if isinstance(field_node, ast.Constant):
                    field = field_node.value
                    if (
                        forbidden(field)
                        and isinstance(field, str)
                        and _field_targets_place(field, receiver, place_names, non_place_names)
                    ):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: controlled Place setattr bypass for {field}"
                        )
                elif (
                    _receiver_is_place(receiver, place_names, non_place_names)
                    and path.resolve() not in APPROVED_DYNAMIC_SETATTR
                ):
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


def test_guard_detects_aliases_loaded_from_place_queries_and_containers() -> None:
    tree = ast.parse(
        """
def mutate(db, places_by_id):
    row = db.query(Place).first()
    candidate = db.get(Place, 1)
    item = places_by_id[1]
    alias = item
    row.verification_status = 'verified'
    candidate.is_published = True
    alias.is_route_eligible = False
"""
    )
    assert {"row", "candidate", "item", "alias"}.issubset(_typed_names(tree, "Place"))


@pytest.mark.parametrize("field", sorted(CONTROLLED_PLACE_INPUT_FIELDS))
def test_owner_registry_covers_every_owned_field(field: str) -> None:
    assert _owner_for(field) is not None or field not in (
        PUBLICATION_OWNED_FIELDS | VERIFICATION_OWNED_FIELDS
    )
