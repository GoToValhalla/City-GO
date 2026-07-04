from __future__ import annotations

from pathlib import Path


def test_city_quality_row_does_not_load_all_city_places_new() -> None:
    source = Path("services/admin_platform_quality.py").read_text(encoding="utf-8")
    body = source.split("def city_quality_row", 1)[1].split("def quality_summary", 1)[0]

    assert ".all()" not in body
    assert "for place in" not in body
    assert "with_entities" in body


def test_admin_performance_foundation_snapshot_models_exist_new() -> None:
    source = Path("models/admin_read_snapshot.py").read_text(encoding="utf-8")

    assert "class AdminOverviewSnapshot" in source
    assert "class CityQualitySnapshot" in source
    assert "class BacklogQueueSnapshot" in source
    assert "computed_at" in source
    assert "stale_after" in source


def test_admin_overview_diagnostics_has_latency_budget_new() -> None:
    source = Path(".github/workflows/admin-diagnostics.yml").read_text(encoding="utf-8")

    assert "OVERVIEW_BOOT_BUDGET_MS = 2000" in source
    assert "/api/admin/overview" in source
    assert "expected <=" in source
