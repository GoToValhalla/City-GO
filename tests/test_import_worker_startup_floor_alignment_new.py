"""Regression for the two independent pre-container startup memory gates
drifting apart.

.github/workflows/run-import-worker-safe.yml's bash STARTUP_HOST_FLOOR_MB
gates the GHA runner's SSH-side preflight, before `docker compose up` is
even invoked. docker-compose.yml's IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB
gates a second, independent check
(data/scripts/check_import_worker_resources.py) that runs inside the
container itself, right before the worker loop starts. A prior fix changed
only the workflow's bash value from 550 to 500, leaving the compose value at
550: the outer gate then let a 527 MB host through, and the inner gate
immediately refused it and exited 1. This test pins both values to 500 and
fails if either one is edited without the other.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_STARTUP_FLOOR_MB = 500


def _compose_startup_floor_mb() -> int:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(
        r"IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB:\s*\$\{IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB:-(\d+)\}",
        text,
    )
    assert match, "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB default not found in docker-compose.yml"
    return int(match.group(1))


def _guard_default_startup_floor_mb() -> int:
    from services.import_worker_defaults import STARTUP_HOST_FLOOR_MB

    return int(STARTUP_HOST_FLOOR_MB)


def _workflow_bash_startup_floor_mb() -> int:
    text = (ROOT / ".github" / "workflows" / "run-import-worker-safe.yml").read_text(encoding="utf-8")
    match = re.search(
        r'IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB="\$\{IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB:-(\d+)\}"',
        text,
    )
    assert match, "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB default not found in run-import-worker-safe.yml"
    return int(match.group(1))


def test_workflow_startup_floor_is_500_new() -> None:
    assert _workflow_bash_startup_floor_mb() == EXPECTED_STARTUP_FLOOR_MB


def test_compose_startup_floor_is_500_new() -> None:
    assert _compose_startup_floor_mb() == EXPECTED_STARTUP_FLOOR_MB


def test_guard_script_default_startup_floor_is_500_new() -> None:
    assert _guard_default_startup_floor_mb() == EXPECTED_STARTUP_FLOOR_MB


def test_external_workflow_and_internal_worker_startup_floors_are_equal_new() -> None:
    """The actual invariant: both independent gates must agree, whatever the
    number is, so a future re-tune of one without the other fails loudly
    instead of reproducing the 527-MiB-through/500-MiB-refused deadlock."""
    assert _workflow_bash_startup_floor_mb() == _compose_startup_floor_mb() == _guard_default_startup_floor_mb()
