"""Single source of truth for every import-worker memory/runtime threshold.

Three genuinely distinct gates exist across the startup preflight
(data/scripts/check_import_worker_resources.py, a separate process running
before the worker container's Python entrypoint even starts), the per-job
claim gate (services/admin_city_import_tasks._safe_mode_block_reason, which
runs once the worker container — and its own baseline memory overhead — is
already live), and the runtime abort guard (the workflow's bash monitor
loop). Conflating any of these into one number is the exact bug this module
exists to prevent: reusing the startup floor as the post-start job-claim
gate made a healthy ~520-531 MB host self-deadlock every queued job forever,
since the container's own overhead permanently keeps MemAvailable below a
threshold that was only ever supposed to gate pre-container startup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.config import settings

logger = logging.getLogger(__name__)


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
    return ImportWorkerThresholds(
        startup_host_floor_mb=settings.import_worker_min_available_memory_mb,
        job_claim_host_floor_mb=settings.import_worker_min_job_claim_memory_mb,
        runtime_host_floor_mb=settings.import_worker_runtime_host_floor_mb,
        runtime_cgroup_percent=settings.import_worker_runtime_cgroup_percent,
        min_container_memory_mb=settings.import_worker_min_container_memory_mb,
        min_container_headroom_mb=settings.import_worker_min_container_headroom_mb,
        max_runtime_seconds=settings.import_worker_max_runtime_seconds,
    )


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
