"""Отчёт full city import run."""

from __future__ import annotations

import json
from pathlib import Path

from data.scripts.full_city_import_report import build_report


def test_build_report_renders_city_table_new(tmp_path: Path) -> None:
    audit = tmp_path / "run"
    audit.mkdir()
    before = {
        "cities": [
            {"city_slug": "kaliningrad", "places_total": 1, "places_published": 1,
             "places_with_real_address": 0, "places_with_public_photo": 0, "places_route_eligible": 0},
        ],
    }
    after = {
        "cities": [
            {"city_slug": "kaliningrad", "places_total": 120, "places_published": 80,
             "places_with_real_address": 40, "places_with_public_photo": 10, "places_route_eligible": 60,
             "places_without_real_address": 40, "category_counts": {"culture": 2, "cafe": 1}},
        ],
    }
    pipeline = {
        "results": [
            {"city": "kaliningrad", "scope": "tourist_core", "status": "success",
             "import_result": {"created": 100}, "address_backfill_result": {"updated": 15},
             "image_enrichment_result": {"created": 5}},
        ],
    }
    (audit / "before_snapshot.json").write_text(json.dumps(before), encoding="utf-8")
    (audit / "after_snapshot.json").write_text(json.dumps(after), encoding="utf-8")
    (audit / "pipeline_result.json").write_text(json.dumps(pipeline), encoding="utf-8")
    (audit / "prod_commit.txt").write_text("abc123\n", encoding="utf-8")
    text = build_report(audit)
    assert "kaliningrad" in text
    assert "1→120" in text
    assert "OSM created=100" in text
