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


def test_workflow_preflight_checks_health_memory_and_running_state_new() -> None:
    text = _workflow_text()

    assert "preflight: public health/ready" in text
    assert "preflight: host memory" in text
    assert "STARTUP_HOST_FLOOR_MB=550" in text
    assert "preflight: import-worker must not already be running" in text
    assert "PREFLIGHT FAILED" in text


def test_workflow_starts_only_import_worker_not_whole_ops_profile_new() -> None:
    text = _workflow_text()

    assert "docker compose up -d --no-deps import-worker" in text
    assert "--profile ops" not in text
    assert "docker compose up -d seed" not in text
    assert "docker compose up -d address-backfill" not in text
    assert "docker compose up -d place-enrichment-export" not in text


def test_workflow_has_runtime_host_cgroup_and_health_guards_new() -> None:
    text = _workflow_text()

    assert "RUNTIME_HOST_FLOOR_MB=256" in text
    assert "RUNTIME_CGROUP_PERCENT=85" in text
    assert "public_health_degraded" in text
    assert "host_memory_floor" in text
    assert "worker_cgroup_soft_limit" in text
    assert "worker_memory_reading_unknown" in text
    assert "docker stats --no-stream" in text
    assert "worker_oom_killed" in text
    assert '"137"' in text


def test_workflow_fails_closed_on_timeout_and_bad_exit_state_new() -> None:
    text = _workflow_text()

    assert "max_runtime_reached" in text
    assert "worker exit code is unknown; failing closed" in text
    assert 'if [ "$WORKER_EXIT_CODE" -ne 0 ]; then' in text
    assert "worker run ended by safety guard" in text


def test_workflow_always_stops_worker_in_cleanup_new() -> None:
    text = _workflow_text()
    monitor_loop_start = text.index('section "monitor loop"')
    cleanup_call_idx = text.index("\n          cleanup\n", monitor_loop_start)
    trap_clear_idx = text.index("trap - EXIT", cleanup_call_idx)

    assert monitor_loop_start < cleanup_call_idx < trap_clear_idx
    assert "cleanup: always stop import-worker" in text
    assert "docker compose stop -t 30 import-worker" in text
    assert "trap cleanup EXIT" in text


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
    assert "UPDATE " not in text
    assert "docker compose up -d --remove-orphans" not in text
