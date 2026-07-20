"""Static contract tests for .github/workflows/route-evaluation.yml.

Root cause of the production incident: DATABASE_URL: sqlite:///:memory:
was unquoted, so the trailing ":memory:" was parsed as a second YAML
mapping key inside the same block -> ScannerError -> GitHub Actions
could not read `name:`, displayed the file path, and recorded a failed
run. These tests parse the file with a real YAML loader (not just
substring checks) so an unquoted-colon regression fails loudly again.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/route-evaluation.yml"


def _load() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_route_evaluation_workflow_is_valid_yaml_new() -> None:
    data = _load()
    assert isinstance(data, dict)
    assert data.get("name") == "CITY GO · TEST · Route Evaluation CI Gate (manual)"


def test_route_evaluation_workflow_only_trigger_is_workflow_dispatch_new() -> None:
    data = _load()
    on_block = data.get(True, data.get("on"))
    assert isinstance(on_block, dict)
    assert list(on_block.keys()) == ["workflow_dispatch"]
    assert "push" not in on_block
    assert "pull_request" not in on_block
    assert "schedule" not in on_block
    assert "workflow_run" not in on_block


def test_route_evaluation_workflow_requires_exact_confirmation_new() -> None:
    data = _load()
    on_block = data.get(True, data.get("on"))
    inputs = on_block["workflow_dispatch"]["inputs"]
    assert "confirmation" in inputs
    assert inputs["confirmation"]["required"] is True

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'inputs.confirmation }}" != "RUN_ROUTE_EVALUATION"' in workflow_text
    assert "exit 1" in workflow_text


def test_route_evaluation_workflow_runs_the_ci_gate_script_new() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "python scripts/run_route_evaluation_ci_gate.py artifacts/route-evaluation" in workflow_text


def test_route_evaluation_workflow_artifact_upload_fails_when_reports_missing_new() -> None:
    data = _load()
    steps = data["jobs"]["route-evaluation"]["steps"]
    upload_step = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload_step["with"]["if-no-files-found"] == "error"
    assert upload_step.get("if") == "always()"


def test_route_evaluation_workflow_database_url_is_quoted_new() -> None:
    """Regression guard for the exact production incident: an unquoted
    sqlite:///:memory: value breaks YAML parsing for the whole file."""
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'DATABASE_URL: "sqlite:///:memory:"' in workflow_text
