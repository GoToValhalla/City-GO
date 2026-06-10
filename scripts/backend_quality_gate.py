from __future__ import annotations

import ast
import configparser
from pathlib import Path

MAX_LINES, MAX_FILES, MIN_FILES, MAX_COMPLEXITY, MIN_COVERAGE = 100, 10, 2, 5, 100
TARGETS = ("api", "core", "db", "models", "routers", "schemas", "services", "scripts")
SKIP_PARTS = {"__pycache__", ".venv", "frontend", "migrations", "app_backup_before_cleanup"}

def run_checks(root: Path) -> list[str]:
    baseline = _load_baseline(root)
    files = _python_files(root)
    return [
        *(_line_violation(path, baseline) for path in files),
        *(_complexity_violation(path, baseline) for path in files),
        *(_module_violation(path, baseline) for path in _module_dirs(root)),
        _coverage_violation(root, baseline),
    ]

def main() -> int:
    violations = tuple(filter(None, run_checks(Path.cwd())))
    tuple(map(print, violations))
    return 1 if violations else 0

def _load_baseline(root: Path) -> set[str]:
    path = root / "scripts" / "backend_quality_baseline.txt"
    lines = path.read_text().splitlines() if path.exists() else ()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}

def _python_files(root: Path) -> tuple[Path, ...]:
    roots = tuple(root / target for target in TARGETS if (root / target).exists())
    return tuple(
        path
        for base in roots
        for path in base.rglob("*.py")
        if not _skipped(path)
    )

def _module_dirs(root: Path) -> tuple[Path, ...]:
    return tuple({path.parent for path in _python_files(root) if path.name != "__init__.py"})

def _skipped(path: Path) -> bool:
    return bool(set(path.parts) & SKIP_PARTS)

def _line_violation(path: Path, baseline: set[str]) -> str:
    rel = path.relative_to(Path.cwd())
    count = len(path.read_text().splitlines())
    if count <= MAX_LINES or f"file:{rel.as_posix()}" in baseline:
        return ""
    return f"file too long: {rel} has {count} lines, max {MAX_LINES}"

def _complexity_violation(path: Path, baseline: set[str]) -> str:
    rel = path.relative_to(Path.cwd())
    if f"file:{rel.as_posix()}" in baseline:
        return ""
    tree = ast.parse(path.read_text(), filename=str(path))
    findings = tuple(filter(None, map(lambda node: _function_issue(node, rel), ast.walk(tree))))
    return "\n".join(findings)

def _function_issue(node: ast.AST, rel: Path) -> str:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    score = 1 + sum(map(_complexity_weight, ast.walk(node)))
    if score <= MAX_COMPLEXITY:
        return ""
    return f"function too complex: {rel}:{node.lineno} {node.name}={score}, max {MAX_COMPLEXITY}"

def _complexity_weight(node: ast.AST) -> int:
    branches = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)
    return int(isinstance(node, branches)) + (len(node.values) - 1 if isinstance(node, ast.BoolOp) else 0)

def _module_violation(path: Path, baseline: set[str]) -> str:
    rel = path.relative_to(Path.cwd())
    if f"module:{rel.as_posix()}" in baseline:
        return ""
    count = len(tuple(item for item in path.glob("*.py") if item.name != "__init__.py"))
    if count <= MAX_FILES and count != 1:
        return ""
    return f"module size violation: {rel} has {count} files, expected {MIN_FILES}..{MAX_FILES}"

def _coverage_violation(root: Path, baseline: set[str]) -> str:
    config = configparser.ConfigParser()
    config.read(root / "pytest.ini")
    addopts = config.get("pytest", "addopts", fallback="")
    marker = "--cov-fail-under="
    floor = next((int(part.split(marker)[1]) for part in addopts.split() if marker in part), 0)
    if floor >= MIN_COVERAGE or "coverage:pytest.ini" in baseline:
        return ""
    return f"coverage floor too low: pytest.ini has {floor}, expected {MIN_COVERAGE}"

if __name__ == "__main__":
    raise SystemExit(main())
