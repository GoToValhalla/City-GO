from __future__ import annotations

from pathlib import Path

import pytest

from data.scripts import check_import_worker_resources as resources


def test_available_memory_mb_reads_memavailable_new(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 2048000 kB\nMemAvailable: 734208 kB\n", encoding="utf-8")

    assert resources.available_memory_mb(meminfo) == 717


def test_validate_resources_passes_with_verified_host_and_cgroup_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", "512")
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", "512")
    monkeypatch.setattr(resources, "available_memory_mb", lambda: 711)
    monkeypatch.setattr(resources, "cgroup_memory_limit_mb", lambda: 512)

    assert resources.validate_resources() == (711, 512)


def test_validate_resources_fails_closed_when_host_memory_unknown_new(monkeypatch) -> None:
    monkeypatch.setattr(resources, "available_memory_mb", lambda: None)

    with pytest.raises(SystemExit, match="MemAvailable is unknown"):
        resources.validate_resources()


def test_validate_resources_blocks_low_host_headroom_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB", "512")
    monkeypatch.setattr(resources, "available_memory_mb", lambda: 511)

    with pytest.raises(SystemExit, match="below required 512 MiB"):
        resources.validate_resources()


def test_validate_resources_fails_closed_when_cgroup_limit_unknown_new(monkeypatch) -> None:
    monkeypatch.setattr(resources, "available_memory_mb", lambda: 711)
    monkeypatch.setattr(resources, "cgroup_memory_limit_mb", lambda: None)

    with pytest.raises(SystemExit, match="cgroup memory limit is unknown/unbounded"):
        resources.validate_resources()


def test_validate_resources_blocks_small_cgroup_limit_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB", "512")
    monkeypatch.setattr(resources, "available_memory_mb", lambda: 711)
    monkeypatch.setattr(resources, "cgroup_memory_limit_mb", lambda: 384)

    with pytest.raises(SystemExit, match="below required 512 MiB"):
        resources.validate_resources()
