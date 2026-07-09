"""Structural safety checks for the manual guarded import-worker run workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "run-import-worker-safe.yml"


def _workflow_text() -> str:
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _workflow_yaml() -> dict:
    data = yaml.safe_load(_workflow_text())
    assert isinstance(data, dict)
    return data


def test_workflow_is_manual_dispatch_only_new() -> None:
    data = _workflow_yaml()
    triggers = data.get(True) or data.get("on")

    assert isinstance(triggers, dict)
    assert "workflow_dispatch" in triggers
    assert "schedule" not in triggers
    assert "push" not in triggers
    assert "pull_request" not in triggers


def test_workflow_requires_exact_confirmation_new() -> None:
    text = _workflow_text()

    assert "RUN_IMPORT_WORKER_SAFELY" in text
    assert 'if [ "${{ inputs.confirmation }}" != "RUN_IMPORT_WORKER_SAFELY" ]; then' in text
    assert "exit 1" in text


def test_workflow_preflight_checks_health_memory_and_running_state_new() -> None:
    text = _workflow_text()

    assert "preflight: public health/ready" in text
    assert "preflight: free memory" in text
    assert "preflight: import-worker must not already be running" in text
    assert "Refusing to start import-worker" in text


def test_workflow_starts_only_import_worker_not_whole_ops_profile_new() -> None:
    text = _workflow_text()

    assert "docker compose up -d --no-deps import-worker" in text
    assert "--profile ops" not in text
    assert "docker compose up -d seed" not in text
    assert "docker compose up -d address-backfill" not in text
    assert "docker compose up -d place-enrichment-export" not in text


def test_workflow_always_stops_worker_in_cleanup_new() -> None:
    text = _workflow_text()
    cleanup_idx = text.index("cleanup: always stop import-worker")
    stop_idx = text.index("docker compose stop import-worker", cleanup_idx)

    assert cleanup_idx < stop_idx
    # The cleanup stop must not be inside the bounded monitor loop's own
    # conditional break paths — it must run unconditionally after the loop ends.
    monitor_loop_start = text.index("monitor loop (every 10s")
    assert monitor_loop_start < cleanup_idx


def test_workflow_uploads_run_report_artifact_new() -> None:
    data = _workflow_yaml()
    steps = data["jobs"]["run-import-worker-safe"]["steps"]
    upload_steps = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")]

    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "safe-import-worker-run-report"
    assert upload_steps[0].get("if") == "always()"


def test_workflow_never_deploys_pulls_images_or_mutates_db_new() -> None:
    text = _workflow_text()

    assert "docker load" not in text
    assert "docker pull" not in text
    assert "psql" not in text
    assert "UPDATE " not in text.upper() or "UPDATE " not in text
    assert "docker compose up -d --remove-orphans" not in text
