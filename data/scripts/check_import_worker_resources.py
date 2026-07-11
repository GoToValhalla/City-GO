"""Fail-closed host and cgroup resource preflight for import-worker.

This script is read-only. It runs inside the import-worker container before the
worker loop and refuses startup when host or container memory cannot be proven
safe.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_MIB = 1024 * 1024
_CGROUP_V1_UNLIMITED = 1 << 60


@dataclass(frozen=True)
class MemorySnapshot:
    host_available_mb: int
    cgroup_limit_mb: int
    cgroup_usage_mb: int

    @property
    def cgroup_headroom_mb(self) -> int:
        return max(0, self.cgroup_limit_mb - self.cgroup_usage_mb)


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}={raw!r}: expected integer MiB") from exc
    if value <= 0:
        raise SystemExit(f"invalid {name}={value}: expected positive MiB")
    return value


def read_host_available_mb(path: Path = Path("/proc/meminfo")) -> int | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _read_bytes(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw or raw == "max":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 0 or value >= _CGROUP_V1_UNLIMITED:
        return None
    return value


def read_cgroup_memory(
    root: Path = Path("/sys/fs/cgroup"),
) -> tuple[int, int] | None:
    """Return finite ``(limit_bytes, usage_bytes)`` for cgroup v2 or v1."""
    v2_limit = _read_bytes(root / "memory.max")
    v2_usage = _read_bytes(root / "memory.current")
    if v2_limit is not None and v2_usage is not None:
        return v2_limit, v2_usage

    v1_root = root / "memory"
    v1_limit = _read_bytes(v1_root / "memory.limit_in_bytes")
    v1_usage = _read_bytes(v1_root / "memory.usage_in_bytes")
    if v1_limit is not None and v1_usage is not None:
        return v1_limit, v1_usage
    return None


def snapshot() -> MemorySnapshot:
    host_available_mb = read_host_available_mb()
    if host_available_mb is None:
        raise SystemExit("import-worker resource guard: host MemAvailable is unknown; refusing to start")

    cgroup = read_cgroup_memory()
    if cgroup is None:
        raise SystemExit("import-worker resource guard: cgroup memory limit/usage is unknown or unbounded; refusing to start")
    limit_bytes, usage_bytes = cgroup
    return MemorySnapshot(
        host_available_mb=host_available_mb,
        cgroup_limit_mb=limit_bytes // _MIB,
        cgroup_usage_mb=usage_bytes // _MIB,
    )


def validate_startup_resources() -> MemorySnapshot:
    min_host_mb = _positive_int_env("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", 550)
    min_container_mb = _positive_int_env("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", 512)
    min_headroom_mb = _positive_int_env("IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB", 400)

    state = snapshot()
    if state.host_available_mb < min_host_mb:
        raise SystemExit(
            "import-worker resource guard: host available memory "
            f"{state.host_available_mb} MiB is below required {min_host_mb} MiB; refusing to start"
        )
    if state.cgroup_limit_mb < min_container_mb:
        raise SystemExit(
            "import-worker resource guard: cgroup memory limit "
            f"{state.cgroup_limit_mb} MiB is below required {min_container_mb} MiB; refusing to start"
        )
    if state.cgroup_headroom_mb < min_headroom_mb:
        raise SystemExit(
            "import-worker resource guard: cgroup memory headroom "
            f"{state.cgroup_headroom_mb} MiB is below required {min_headroom_mb} MiB; refusing to start"
        )
    return state


def main() -> int:
    state = validate_startup_resources()
    print(
        "import-worker resource preflight passed: "
        f"host_available_mb={state.host_available_mb} "
        f"cgroup_limit_mb={state.cgroup_limit_mb} "
        f"cgroup_usage_mb={state.cgroup_usage_mb} "
        f"cgroup_headroom_mb={state.cgroup_headroom_mb}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
