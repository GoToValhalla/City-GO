"""Regression tests for the centralized import-worker threshold module:
startup floor and job-claim floor must be genuinely separate values, and
the effective thresholds must be logged."""

from __future__ import annotations

import logging
from pathlib import Path

from services import import_worker_thresholds as thresholds_module


def test_startup_and_job_claim_floors_are_independent_new(monkeypatch) -> None:
    monkeypatch.setattr(thresholds_module.settings, "import_worker_min_available_memory_mb", 550)
    monkeypatch.setattr(thresholds_module.settings, "import_worker_min_job_claim_memory_mb", 350)

    result = thresholds_module.effective_thresholds()

    assert result.startup_host_floor_mb == 550
    assert result.job_claim_host_floor_mb == 350
    assert result.job_claim_host_floor_mb < result.startup_host_floor_mb


def test_job_claim_default_is_compatible_with_normal_worker_overhead_new() -> None:
    """The default job-claim floor must sit comfortably below a realistic
    post-start MemAvailable (520-531 MB observed in production) and
    comfortably above the runtime abort floor (256 MB) — otherwise it
    either self-deadlocks or provides no real safety margin."""
    result = thresholds_module.effective_thresholds()

    assert result.job_claim_host_floor_mb < 520
    assert result.job_claim_host_floor_mb > result.runtime_host_floor_mb


def test_effective_thresholds_are_logged_new(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="services.import_worker_thresholds"):
        thresholds_module.log_effective_thresholds()

    assert any("import_worker_effective_thresholds" in record.message for record in caplog.records)


def test_production_compose_keeps_startup_floor_at_550_and_job_claim_floor_lower_new() -> None:
    """The pre-container startup floor must stay at 550 MB in production
    (docker-compose.yml), while the new job-claim floor is a genuinely
    separate, lower value — this task changes only the post-start gate."""
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB: 550" in compose
    assert "IMPORT_WORKER_MIN_JOB_CLAIM_MEMORY_MB: 350" in compose
