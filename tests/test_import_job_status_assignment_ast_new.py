"""Repository-level regression: no code outside the transition service,
Alembic migrations, or the explicit legacy-repair tool may assign
`<name>.status = "..."` to a CityAdminImportJob instance directly.

Independent code review of commit 968e54c7 (the immutable-lifecycle fix)
found several such direct writes surviving despite _transition existing:
run_city_import_job wrote job.status = "running" over a phase's already-
terminal outcome, and the sub-phase pipelines (services/import_pipeline/
runner.py, services/import_pipeline/enrichment_only.py,
services/import_pipeline_foundation.py) each terminalized the parent job
themselves mid-flow. All of those now route through
admin_city_import_job_service._transition, which is the one place allowed
to write CityAdminImportJob.status (it validates the transition against
_ALLOWED_TRANSITIONS and fails closed on anything invalid).

This is a source-text AST scan, deliberately: it proves the absence of a
direct assignment at every module CityAdminImportJob rows pass through,
and fails loudly the moment one is reintroduced, rather than relying on
runtime test coverage (which only catches the specific status values a
test happens to construct) alone.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every module that touches a CityAdminImportJob instance during its
# normal (non-migration, non-repair-tool) lifecycle.
SCANNED_FILES = (
    "services/admin_city_import_job_service.py",
    "services/admin_city_import_tasks.py",
    "services/admin_city_import_job_finish.py",
    "services/admin_city_import_job_payload.py",
    "services/admin_import_job_diagnostic_service.py",
    "services/import_pipeline/runner.py",
    "services/import_pipeline/enrichment_only.py",
    "services/import_pipeline_foundation.py",
    "routers/admin_import_jobs.py",
    "routers/admin_import_queue.py",
    "routers/admin_import_pipeline.py",
)

# The only function allowed to assign `<name>.status = <string literal>`
# to a job object — every other assignment in SCANNED_FILES must instead
# call this function.
ALLOWED_ASSIGNER = "_transition"


def _source(path: str) -> str:
    full = REPO_ROOT / path
    assert full.exists(), f"expected file missing: {path}"
    return full.read_text(encoding="utf-8")


def _direct_status_assignments(source: str, path: str) -> list[str]:
    """Find every `<something>.status = <string literal>` assignment NOT
    inside a function named _transition (or its own definition body)."""
    tree = ast.parse(source, filename=path)
    violations: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.current_function: str | None = None

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            previous = self.current_function
            self.current_function = node.name
            self.generic_visit(node)
            self.current_function = previous

        def visit_Assign(self, node: ast.Assign) -> None:
            if self.current_function != ALLOWED_ASSIGNER:
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr == "status"
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        violations.append(
                            f"{path}:{node.lineno}: direct status assignment "
                            f"outside {ALLOWED_ASSIGNER}() (in {self.current_function or '<module>'})"
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def test_no_direct_job_status_assignment_outside_transition_service_new():
    all_violations: list[str] = []
    for path in SCANNED_FILES:
        source = _source(path)
        all_violations.extend(_direct_status_assignments(source, path))
    assert not all_violations, (
        "Direct CityAdminImportJob.status assignments found outside "
        f"{ALLOWED_ASSIGNER}():\n" + "\n".join(all_violations)
    )


def test_transition_service_itself_still_has_the_one_allowed_assignment_new():
    """Guards against the AST scan silently passing because _transition was
    renamed/removed/gutted — the one legitimate assignment must still
    exist somewhere in the codebase."""
    source = _source("services/admin_city_import_job_service.py")
    tree = ast.parse(source)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ALLOWED_ASSIGNER:
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Assign)
                    and any(isinstance(t, ast.Attribute) and t.attr == "status" for t in inner.targets)
                ):
                    found = True
    assert found, f"{ALLOWED_ASSIGNER}() must contain the one allowed job.status assignment"
