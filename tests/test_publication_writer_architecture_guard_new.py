from __future__ import annotations

import ast
from pathlib import Path

import pytest

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
PUBLICATION_FIELDS = frozenset(
    {
        "publication_status",
        "publication_reason_code",
        "publication_reason_details",
        "is_published",
        "is_visible_in_catalog",
        "is_searchable",
        "is_route_eligible",
    }
)


def _python_files() -> list[Path]:
    result: list[Path] = []
    for root in PRODUCTION_ROOTS:
        if root.exists():
            result.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(set(result))


def _attribute_name(node: ast.AST) -> str | None:
    return node.attr if isinstance(node, ast.Attribute) else None


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
        result: list[ast.AST] = []
        for item in node.elts:
            result.extend(_flatten_targets(item))
        return result
    return [node]


def _violations(path: Path) -> list[str]:
    if path.resolve() == CANONICAL_WRITER:
        return []
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        for target in _assignment_targets(node):
            for flattened in _flatten_targets(target):
                field = _attribute_name(flattened)
                if field in PUBLICATION_FIELDS:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: direct assignment to {field}")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                field = node.args[1].value
                if field in PUBLICATION_FIELDS:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: setattr bypass for {field}")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"update", "values"}:
                for keyword in node.keywords:
                    if keyword.arg in PUBLICATION_FIELDS:
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: bulk update bypass for {keyword.arg}"
                        )
                for argument in node.args:
                    if isinstance(argument, ast.Dict):
                        for key in argument.keys:
                            if isinstance(key, ast.Constant) and key.value in PUBLICATION_FIELDS:
                                violations.append(
                                    f"{path.relative_to(ROOT)}:{node.lineno}: mapping update bypass for {key.value}"
                                )

    normalized = " ".join(text.lower().split())
    if "update places" in normalized:
        violations.append(f"{path.relative_to(ROOT)}: raw UPDATE places statement")
    return violations


@title("Only canonical writer may mutate Place publication state")
def test_no_publication_state_mutation_bypasses() -> None:
    violations = [violation for path in _python_files() for violation in _violations(path)]
    assert violations == [], "Publication writer bypasses found:\n" + "\n".join(violations)


@pytest.mark.parametrize("field", sorted(PUBLICATION_FIELDS))
@title("Architecture guard recognizes every protected publication field")
def test_publication_guard_field_registry_is_complete(field: str) -> None:
    assert field in PUBLICATION_FIELDS
