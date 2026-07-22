"""Single source of truth for every import-worker memory/runtime threshold.

Three genuinely distinct gates exist across the startup preflight
(data/scripts/check_import_worker_resources.py), the per-job claim gate
(services/admin_city_import_tasks._safe_mode_block_reason), and the runtime
abort guard (the workflow's bash monitor loop). Conflating any of these into
one number is the exact bug this module exists to prevent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.config import settings
from services.import_worker_defaults import (
    JOB_CLAIM_HOST_FLOOR_MB,
    MAX_RUNTIME_SECONDS,
    MIN_CONTAINER_HEADROOM_MB,
    MIN_CONTAINER_MEMORY_MB,
    RUNTIME_CGROUP_PERCENT,
    RUNTIME_HOST_FLOOR_MB,
    STARTUP_HOST_FLOOR_MB,
    validate_threshold_values,
)

logger = logging.getLogger(__name__)

# Re-export contract defaults so callers/tests have one import path.
DEFAULT_STARTUP_HOST_FLOOR_MB = STARTUP_HOST_FLOOR_MB
DEFAULT_JOB_CLAIM_HOST_FLOOR_MB = JOB_CLAIM_HOST_FLOOR_MB
DEFAULT_RUNTIME_HOST_FLOOR_MB = RUNTIME_HOST_FLOOR_MB
DEFAULT_RUNTIME_CGROUP_PERCENT = RUNTIME_CGROUP_PERCENT
DEFAULT_MIN_CONTAINER_MEMORY_MB = MIN_CONTAINER_MEMORY_MB
DEFAULT_MIN_CONTAINER_HEADROOM_MB = MIN_CONTAINER_HEADROOM_MB
DEFAULT_MAX_RUNTIME_SECONDS = MAX_RUNTIME_SECONDS


@dataclass(frozen=True)
class ImportWorkerThresholds:
    startup_host_floor_mb: int
    job_claim_host_floor_mb: int
    runtime_host_floor_mb: int
    runtime_cgroup_percent: int
    min_container_memory_mb: int
    min_container_headroom_mb: int
    max_runtime_seconds: int


def effective_thresholds() -> ImportWorkerThresholds:
    thresholds = ImportWorkerThresholds(
        startup_host_floor_mb=settings.import_worker_min_available_memory_mb,
        job_claim_host_floor_mb=settings.import_worker_min_job_claim_memory_mb,
        runtime_host_floor_mb=settings.import_worker_runtime_host_floor_mb,
        runtime_cgroup_percent=settings.import_worker_runtime_cgroup_percent,
        min_container_memory_mb=settings.import_worker_min_container_memory_mb,
        min_container_headroom_mb=settings.import_worker_min_container_headroom_mb,
        max_runtime_seconds=settings.import_worker_max_runtime_seconds,
    )
    validate_threshold_values(
        startup_host_floor_mb=thresholds.startup_host_floor_mb,
        job_claim_host_floor_mb=thresholds.job_claim_host_floor_mb,
        runtime_host_floor_mb=thresholds.runtime_host_floor_mb,
        runtime_cgroup_percent=thresholds.runtime_cgroup_percent,
        min_container_memory_mb=thresholds.min_container_memory_mb,
        min_container_headroom_mb=thresholds.min_container_headroom_mb,
        max_runtime_seconds=thresholds.max_runtime_seconds,
    )
    return thresholds


def log_effective_thresholds(thresholds: ImportWorkerThresholds | None = None) -> ImportWorkerThresholds:
    thresholds = thresholds or effective_thresholds()
    logger.info(
        "import_worker_effective_thresholds startup_host_floor_mb=%s job_claim_host_floor_mb=%s "
        "runtime_host_floor_mb=%s runtime_cgroup_percent=%s min_container_memory_mb=%s "
        "min_container_headroom_mb=%s max_runtime_seconds=%s",
        thresholds.startup_host_floor_mb,
        thresholds.job_claim_host_floor_mb,
        thresholds.runtime_host_floor_mb,
        thresholds.runtime_cgroup_percent,
        thresholds.min_container_memory_mb,
        thresholds.min_container_headroom_mb,
        thresholds.max_runtime_seconds,
    )
    return thresholds
