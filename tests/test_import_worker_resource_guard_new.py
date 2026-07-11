from __future__ import annotations

from pathlib import Path

import pytest

from data.scripts import check_import_worker_resources as guard


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_reads_cgroup_v2_limit_and_usage_new(tmp_path: Path) -> None:
    _write(tmp_path / "memory.max", str(512 * 1024 * 1024))
    _write(tmp_path / "memory.current", str(64 * 1024 * 1024))

    assert guard.read_cgroup_memory(tmp_path) == (512 * 1024 * 1024, 64 * 1024 * 1024)


def test_reads_cgroup_v1_limit_and_usage_new(tmp_path: Path) -> None:
    _write(tmp_path / "memory" / "memory.limit_in_bytes", str(512 * 1024 * 1024))
    _write(tmp_path / "memory" / "memory.usage_in_bytes", str(80 * 1024 * 1024))

    assert guard.read_cgroup_memory(tmp_path) == (512 * 1024 * 1024, 80 * 1024 * 1024)


def test_unknown_or_unbounded_cgroup_fails_closed_new(tmp_path: Path) -> None:
    _write(tmp_path / "memory.max", "max")
    _write(tmp_path / "memory.current", "0")

    assert guard.read_cgroup_memory(tmp_path) is None


def test_startup_allows_sufficient_host_and_cgroup_headroom_new(monkeypatch) -> None:
    monkeypatch.setattr(
        guard,
        "snapshot",
        lambda: guard.MemorySnapshot(host_available_mb=711, cgroup_limit_mb=512, cgroup_usage_mb=64),
    )
    monkeypatch.setenv("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", "600")
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", "512")
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB", "400")

    state = guard.validate_startup_resources()

    assert state.host_available_mb == 711
    assert state.cgroup_headroom_mb == 448


def test_startup_blocks_below_host_floor_new(monkeypatch) -> None:
    monkeypatch.setattr(
        guard,
        "snapshot",
        lambda: guard.MemorySnapshot(host_available_mb=599, cgroup_limit_mb=512, cgroup_usage_mb=32),
    )
    monkeypatch.setenv("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", "600")

    with pytest.raises(SystemExit, match="host available memory"):
        guard.validate_startup_resources()


def test_startup_blocks_insufficient_cgroup_limit_new(monkeypatch) -> None:
    monkeypatch.setattr(
        guard,
        "snapshot",
        lambda: guard.MemorySnapshot(host_available_mb=800, cgroup_limit_mb=384, cgroup_usage_mb=10),
    )
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", "512")

    with pytest.raises(SystemExit, match="cgroup memory limit"):
        guard.validate_startup_resources()


def test_startup_blocks_insufficient_cgroup_headroom_new(monkeypatch) -> None:
    monkeypatch.setattr(
        guard,
        "snapshot",
        lambda: guard.MemorySnapshot(host_available_mb=800, cgroup_limit_mb=512, cgroup_usage_mb=120),
    )
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB", "400")

    with pytest.raises(SystemExit, match="cgroup memory headroom"):
        guard.validate_startup_resources()
