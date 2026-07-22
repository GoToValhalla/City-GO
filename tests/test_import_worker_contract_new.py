"""Import-worker defaults/threshold/terminal-outcome contract tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.config import Settings
from services import import_worker_defaults as defaults
from services import import_worker_terminal_outcomes as outcomes
from services import import_worker_thresholds as thresholds_module

ROOT = Path(__file__).resolve().parent.parent


def test_startup_claim_runtime_floors_remain_distinct_new() -> None:
    assert defaults.STARTUP_HOST_FLOOR_MB != defaults.JOB_CLAIM_HOST_FLOOR_MB
    assert defaults.JOB_CLAIM_HOST_FLOOR_MB != defaults.RUNTIME_HOST_FLOOR_MB
    assert defaults.STARTUP_HOST_FLOOR_MB != defaults.RUNTIME_HOST_FLOOR_MB
    defaults.validate_threshold_values(
        startup_host_floor_mb=defaults.STARTUP_HOST_FLOOR_MB,
        job_claim_host_floor_mb=defaults.JOB_CLAIM_HOST_FLOOR_MB,
        runtime_host_floor_mb=defaults.RUNTIME_HOST_FLOOR_MB,
        runtime_cgroup_percent=defaults.RUNTIME_CGROUP_PERCENT,
        min_container_memory_mb=defaults.MIN_CONTAINER_MEMORY_MB,
        min_container_headroom_mb=defaults.MIN_CONTAINER_HEADROOM_MB,
        max_runtime_seconds=defaults.MAX_RUNTIME_SECONDS,
    )


def test_settings_defaults_match_authoritative_contract_new() -> None:
    settings = Settings()
    assert settings.import_worker_min_available_memory_mb == defaults.STARTUP_HOST_FLOOR_MB
    assert settings.import_worker_min_job_claim_memory_mb == defaults.JOB_CLAIM_HOST_FLOOR_MB
    assert settings.import_worker_runtime_host_floor_mb == defaults.RUNTIME_HOST_FLOOR_MB
    assert settings.import_worker_runtime_cgroup_percent == defaults.RUNTIME_CGROUP_PERCENT
    assert settings.import_worker_min_container_memory_mb == defaults.MIN_CONTAINER_MEMORY_MB
    assert settings.import_worker_min_container_headroom_mb == defaults.MIN_CONTAINER_HEADROOM_MB
    assert settings.import_worker_max_runtime_seconds == defaults.MAX_RUNTIME_SECONDS
    assert settings.import_worker_max_full_import_places_low_memory == defaults.MAX_FULL_IMPORT_PLACES_LOW_MEMORY


def test_compose_and_workflows_use_named_contract_env_new() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    run_wf = (ROOT / ".github/workflows/run-import-worker-safe.yml").read_text(encoding="utf-8")
    verify_wf = (ROOT / ".github/workflows/verify-import-worker-safety.yml").read_text(encoding="utf-8")

    assert f"${{{defaults.ENV_STARTUP_HOST_FLOOR}:-{defaults.STARTUP_HOST_FLOOR_MB}}}" in compose
    assert f"${{{defaults.ENV_JOB_CLAIM_HOST_FLOOR}:-{defaults.JOB_CLAIM_HOST_FLOOR_MB}}}" in compose
    assert f"${{{defaults.ENV_MAX_RUNTIME}:-{defaults.MAX_RUNTIME_SECONDS}}}" in compose
    assert defaults.ENV_STARTUP_HOST_FLOOR in run_wf
    assert defaults.ENV_JOB_CLAIM_HOST_FLOOR in run_wf
    assert f'"{defaults.ENV_MAX_RUNTIME}": "{defaults.MAX_RUNTIME_SECONDS}"' in verify_wf
    assert f'"{defaults.ENV_JOB_CLAIM_HOST_FLOOR}": "{defaults.JOB_CLAIM_HOST_FLOOR_MB}"' in verify_wf
    assert f'"{defaults.ENV_MAX_RUNTIME}": "300"' not in verify_wf


def test_invalid_threshold_ordering_fails_validation_new() -> None:
    with pytest.raises(ValueError, match="startup_host_floor_mb > job_claim_host_floor_mb"):
        defaults.validate_threshold_values(
            startup_host_floor_mb=300,
            job_claim_host_floor_mb=350,
            runtime_host_floor_mb=256,
            runtime_cgroup_percent=85,
            min_container_memory_mb=512,
            min_container_headroom_mb=400,
            max_runtime_seconds=900,
        )


def test_workflow_timeout_covers_max_runtime_with_cleanup_margin_new() -> None:
    run_wf = (ROOT / ".github/workflows/run-import-worker-safe.yml").read_text(encoding="utf-8")
    match = re.search(r"timeout-minutes:\s*(\d+)", run_wf)
    assert match is not None
    timeout_minutes = int(match.group(1))
    assert defaults.workflow_timeout_covers_max_runtime(
        max_runtime_seconds=defaults.MAX_RUNTIME_SECONDS,
        workflow_timeout_minutes=timeout_minutes,
    )
    assert timeout_minutes == defaults.WORKFLOW_TIMEOUT_MINUTES


def test_terminal_outcome_classes_and_exit_policy_new() -> None:
    assert outcomes.classify_terminal_status("success") == outcomes.OUTCOME_SUCCESS
    assert outcomes.classify_terminal_status("success_with_warnings") == outcomes.OUTCOME_SUCCESS
    assert outcomes.classify_terminal_status("partial_success") == outcomes.OUTCOME_PARTIAL
    assert outcomes.classify_terminal_status("failed") == outcomes.OUTCOME_FAILED
    assert outcomes.classify_terminal_status("stalled") == outcomes.OUTCOME_EXTERNAL_STOP
    assert outcomes.classify_terminal_status("cancelled") == outcomes.OUTCOME_EXTERNAL_STOP
    assert outcomes.classify_terminal_status("running") == outcomes.OUTCOME_INCOMPLETE

    assert outcomes.process_success_exit(outcomes.OUTCOME_SUCCESS) is True
    assert outcomes.process_success_exit(outcomes.OUTCOME_PARTIAL) is True
    assert outcomes.process_success_exit(outcomes.OUTCOME_FAILED) is False
    assert outcomes.process_success_exit(outcomes.OUTCOME_EXTERNAL_STOP) is False
    assert outcomes.process_success_exit(outcomes.OUTCOME_INCOMPLETE) is False

    assert "stalled" in outcomes.ALL_TERMINAL_JOB_STATUSES
    assert "cancelled" in outcomes.ALL_TERMINAL_JOB_STATUSES


def test_effective_thresholds_reject_unsafe_settings_new(monkeypatch) -> None:
    monkeypatch.setattr(thresholds_module.settings, "import_worker_min_available_memory_mb", 200)
    monkeypatch.setattr(thresholds_module.settings, "import_worker_min_job_claim_memory_mb", 350)
    monkeypatch.setattr(thresholds_module.settings, "import_worker_runtime_host_floor_mb", 256)
    with pytest.raises(ValueError, match="startup_host_floor_mb > job_claim_host_floor_mb"):
        thresholds_module.effective_thresholds()
