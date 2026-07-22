from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchitectureViolation:
    path: str
    line: int
    rule: str
    detail: str


def imported_modules(path: Path) -> tuple[tuple[str, int], ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            rows.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            rows.append((node.module, node.lineno))
    return tuple(rows)


def forbidden_dependency_violations(
    *, root: Path, sources: tuple[Path, ...], forbidden_prefixes: tuple[str, ...], rule: str
) -> tuple[ArchitectureViolation, ...]:
    violations: list[ArchitectureViolation] = []
    for path in sources:
        for module, line in imported_modules(path):
            if any(module.startswith(prefix) for prefix in forbidden_prefixes):
                violations.append(
                    ArchitectureViolation(str(path.relative_to(root)), line, rule, module)
                )
    return tuple(violations)


def transaction_calls(path: Path) -> tuple[tuple[str, int], ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {"commit", "rollback", "flush", "begin", "begin_nested"}:
            calls.append((node.func.attr, node.lineno))
    return tuple(calls)


def model_imports(path: Path) -> tuple[tuple[str, int], ...]:
    return tuple(
        (module, line)
        for module, line in imported_modules(path)
        if module == "models" or module.startswith("models.")
    )
