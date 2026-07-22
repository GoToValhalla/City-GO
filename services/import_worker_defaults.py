"""Authoritative import-worker memory/runtime defaults and env contract.

Memory gates stay intentionally distinct:
- startup_host_floor: pre-container / preflight host MemAvailable
- job_claim_host_floor: post-start claim gate (lower; container already live)
- runtime_host_floor: monitor abort floor during a running container
"""

from __future__ import annotations

STARTUP_HOST_FLOOR_MB = 500
JOB_CLAIM_HOST_FLOOR_MB = 350
RUNTIME_HOST_FLOOR_MB = 256
RUNTIME_CGROUP_PERCENT = 85
MIN_CONTAINER_MEMORY_MB = 512
MIN_CONTAINER_HEADROOM_MB = 400
MAX_RUNTIME_SECONDS = 900
WORKFLOW_TIMEOUT_MINUTES = 20
WORKFLOW_CLEANUP_MARGIN_SECONDS = 300
MAX_FULL_IMPORT_PLACES_LOW_MEMORY = 1
SAFE_MODE_DEFAULT = False  # local/CI; compose forces true for ops profile

ENV_STARTUP_HOST_FLOOR = "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB"
ENV_JOB_CLAIM_HOST_FLOOR = "IMPORT_WORKER_MIN_JOB_CLAIM_MEMORY_MB"
ENV_RUNTIME_HOST_FLOOR = "IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB"
ENV_RUNTIME_CGROUP_PERCENT = "IMPORT_WORKER_RUNTIME_CGROUP_PERCENT"
ENV_MIN_CONTAINER_MEMORY = "IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB"
ENV_MIN_CONTAINER_HEADROOM = "IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB"
ENV_MAX_RUNTIME = "IMPORT_WORKER_MAX_RUNTIME_SECONDS"
ENV_MAX_FULL_IMPORT_PLACES = "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY"


def validate_threshold_values(
    *,
    startup_host_floor_mb: int,
    job_claim_host_floor_mb: int,
    runtime_host_floor_mb: int,
    runtime_cgroup_percent: int,
    min_container_memory_mb: int,
    min_container_headroom_mb: int,
    max_runtime_seconds: int,
) -> None:
    """Fail closed on contradictory / unsafe threshold combinations."""
    positive = {
        "startup_host_floor_mb": startup_host_floor_mb,
        "job_claim_host_floor_mb": job_claim_host_floor_mb,
        "runtime_host_floor_mb": runtime_host_floor_mb,
        "min_container_memory_mb": min_container_memory_mb,
        "min_container_headroom_mb": min_container_headroom_mb,
        "max_runtime_seconds": max_runtime_seconds,
    }
    for name, value in positive.items():
        if int(value) <= 0:
            raise ValueError(f"import-worker threshold {name} must be > 0 (got {value})")
    if not (1 <= int(runtime_cgroup_percent) <= 100):
        raise ValueError(
            f"import-worker runtime_cgroup_percent must be 1..100 (got {runtime_cgroup_percent})"
        )
    if not (startup_host_floor_mb > job_claim_host_floor_mb > runtime_host_floor_mb):
        raise ValueError(
            "import-worker thresholds must satisfy "
            "startup_host_floor_mb > job_claim_host_floor_mb > runtime_host_floor_mb "
            f"(got {startup_host_floor_mb} > {job_claim_host_floor_mb} > {runtime_host_floor_mb})"
        )
    if min_container_headroom_mb >= min_container_memory_mb:
        raise ValueError(
            "import-worker min_container_headroom_mb must be < min_container_memory_mb "
            f"(got headroom={min_container_headroom_mb}, limit={min_container_memory_mb})"
        )


def workflow_timeout_covers_max_runtime(
    *,
    max_runtime_seconds: int,
    workflow_timeout_minutes: int,
    cleanup_margin_seconds: int = WORKFLOW_CLEANUP_MARGIN_SECONDS,
) -> bool:
    return int(workflow_timeout_minutes) * 60 >= int(max_runtime_seconds) + int(cleanup_margin_seconds)
