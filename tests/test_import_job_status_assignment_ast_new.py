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


# --- terminal-field write consolidation (finalize_import_job) --------------
#
# Architectural consolidation: within the finalization-AUTHORITY layer
# (the modules that own a job's final terminal outcome — the runners in
# admin_city_import_job_service.py, the worker loop and its exception
# handler in admin_city_import_tasks.py, and the admin mark-stalled
# endpoint), finalize_import_job is the ONLY function allowed to assign
# CityAdminImportJob.finished_at / .last_error directly (current_step and
# step_details are excluded — runners legitimately update those as
# PROGRESS during execution, per the task's own "runners may update
# progress" allowance; finished_at/last_error are unambiguously
# terminal-only fields with no legitimate mid-flight meaning at this
# layer). Every terminal write of those two fields at this layer must
# instead go through finalize_import_job's own `fields=` dict.
#
# Deliberately narrower than SCANNED_FILES (which also covers the
# .status-assignment guard): the sub-pipeline phase modules
# (services/import_pipeline/runner.py, enrichment_only.py,
# import_pipeline_foundation.py) write their OWN phase-scoped
# finished_at/last_error as legacy per-phase bookkeeping, read back by
# their caller (e.g. run_city_import_job reads job.last_error from the
# legacy phase to fold into the combined value it passes to
# finalize_import_job) — those are upstream inputs to the one real
# terminal decision, not a second terminal authority, and refactoring that
# layer is out of scope for this task's named 9 functions.
TERMINAL_FIELD_SCANNED_FILES = (
    "services/admin_city_import_job_service.py",
    "services/admin_city_import_tasks.py",
    "routers/admin_import_queue.py",
)

TERMINAL_ONLY_FIELDS = frozenset({"finished_at", "last_error"})

# Functions allowed to assign these fields directly: finalize_import_job
# itself (the field writes happen via setattr in a loop, not a literal
# assignment, so this AST check does not even fire inside it — listed here
# for clarity/documentation only), and the two administrative call sites
# that still legitimately construct a `fields=`/direct-write payload
# alongside their own pre-checks before delegating to finalize_import_job.
TERMINAL_FIELD_ALLOWED_FUNCTIONS = frozenset({"finalize_import_job", "_transition"})


def _direct_terminal_field_assignments(source: str, path: str) -> list[str]:
    """Find every `<something>.finished_at = ...` / `<something>.last_error
    = ...` assignment outside TERMINAL_FIELD_ALLOWED_FUNCTIONS. A dict
    literal key (e.g. fields={"finished_at": ...}) is NOT an attribute
    assignment and is correctly ignored by this scan — that is exactly the
    approved pattern (build a plain dict, pass it to finalize_import_job)."""
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
            if self.current_function not in TERMINAL_FIELD_ALLOWED_FUNCTIONS:
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr in TERMINAL_ONLY_FIELDS:
                        violations.append(
                            f"{path}:{node.lineno}: direct .{target.attr} assignment outside "
                            f"finalize_import_job's fields= dict (in {self.current_function or '<module>'})"
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def test_no_direct_terminal_field_assignment_outside_finalize_import_job_new():
    all_violations: list[str] = []
    for path in TERMINAL_FIELD_SCANNED_FILES:
        source = _source(path)
        all_violations.extend(_direct_terminal_field_assignments(source, path))
    assert not all_violations, (
        "Direct CityAdminImportJob terminal-field (finished_at/last_error) "
        "assignments found outside finalize_import_job's fields= dict:\n" + "\n".join(all_violations)
    )


def test_only_one_function_acquires_a_row_lock_and_checks_job_status_new():
    """Guards against a second, independently-implemented finalization
    primitive being reintroduced (the exact architectural drift this task
    consolidates away: status-only checks, then row locks, then
    stale-refresh, each patched in isolation across multiple functions
    over time). Scans for the combination of `.with_for_update()` AND a
    comparison against `.status` inside the SAME function — the structural
    signature of "this function re-implements lock-check-write" — and
    fails if any function other than finalize_import_job has both.

    claim_queued_job is deliberately exempt: it performs the ONE other
    legitimate row-locked status check in the codebase (queued -> running),
    which is a distinct operation from terminal finalization and is not
    itself a duplicate of finalize_import_job's logic."""
    exempt = {"finalize_import_job", "claim_queued_job"}
    source = _source("services/admin_city_import_job_service.py")
    tree = ast.parse(source)
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name in exempt:
            continue
        has_for_update = False
        has_status_check = False
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == "with_for_update":
                has_for_update = True
            if isinstance(inner, ast.Compare):
                for side in (inner.left, *inner.comparators):
                    if isinstance(side, ast.Attribute) and side.attr == "status":
                        has_status_check = True
        if has_for_update and has_status_check:
            violations.append(node.name)

    assert not violations, (
        "Function(s) reimplementing row-lock + status-check outside "
        f"finalize_import_job (possible duplicate finalization logic): {violations}"
    )
