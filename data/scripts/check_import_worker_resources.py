"""Fail-closed runtime resource preflight for the manual import worker.

This script runs inside the import-worker container before the worker loop.
It verifies both host headroom and the container cgroup memory ceiling. It
never mutates application or queue state.
"""

from __future__ import annotations

import os
from pathlib import Path

_MIB = 1024 * 1024


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}={raw!r}: expected integer MiB") from exc
    if value <= 0:
        raise SystemExit(f"invalid {name}={value}: expected positive MiB")
    return value


def available_memory_mb(path: Path = Path("/proc/meminfo")) -> int | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def cgroup_memory_limit_mb() -> int | None:
    candidates = (
        Path("/sys/fs/cgroup/memory.max"),
        Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
    )
    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not raw or raw == "max":
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        # Some cgroup v1 hosts expose a huge sentinel for "unlimited".
        if value >= 1 << 60:
            return None
        return value // _MIB
    return None


def validate_resources() -> tuple[int, int]:
    min_host_mb = _positive_int_env("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", 512)
    min_container_mb = _positive_int_env("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", 512)

    host_available_mb = available_memory_mb()
    if host_available_mb is None:
        raise SystemExit("import-worker resource guard: host MemAvailable is unknown; refusing to start")
    if host_available_mb < min_host_mb:
        raise SystemExit(
            "import-worker resource guard: host available memory "
            f"{host_available_mb} MiB is below required {min_host_mb} MiB; refusing to start"
        )

    container_limit_mb = cgroup_memory_limit_mb()
    if container_limit_mb is None:
        raise SystemExit("import-worker resource guard: cgroup memory limit is unknown/unbounded; refusing to start")
    if container_limit_mb < min_container_mb:
        raise SystemExit(
            "import-worker resource guard: cgroup memory limit "
            f"{container_limit_mb} MiB is below required {min_container_mb} MiB; refusing to start"
        )

    return host_available_mb, container_limit_mb


def main() -> int:
    host_available_mb, container_limit_mb = validate_resources()
    print(
        "import-worker resource preflight passed: "
        f"host_available_mb={host_available_mb} container_limit_mb={container_limit_mb}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
