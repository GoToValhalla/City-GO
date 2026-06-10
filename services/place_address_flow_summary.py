"""Сборка summary для address recovery flow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

EXPORT_DIR = Path("data/exports/address_recovery")


def city_metrics(report: dict[str, Any]) -> dict[str, int]:
    return {
        "total": int(report.get("total_places") or 0),
        "with_real": int(report.get("with_real_address") or 0),
        "without": int(report.get("without_address") or 0),
        "generic": int(report.get("generic_address_count") or 0),
        "placeholders": int(report.get("literal_placeholder_count") or 0),
    }


def count_apply_skipped(stats: dict[str, Any]) -> int:
    keys = (
        "skipped_should_apply_false", "skipped_existing_real_address",
        "skipped_missing_place", "skipped_empty_proposed", "skipped_policy",
    )
    return sum(int(stats.get(key) or 0) for key in keys)


def build_flow_summary(
    before: dict[str, Any],
    after: dict[str, Any],
    city_results: list[dict[str, Any]],
    before_path: str,
    after_path: str,
    apply_changes: bool,
) -> dict[str, Any]:
    cities = []
    for item in city_results:
        slug = str(item["city_slug"])
        cities.append({
            **item,
            "with_real_before": city_metrics(before.get(slug, {}))["with_real"],
            "without_before": city_metrics(before.get(slug, {}))["without"],
            "generic_before": city_metrics(before.get(slug, {}))["generic"],
            "with_real_after": city_metrics(after.get(slug, {}))["with_real"],
            "without_after": city_metrics(after.get(slug, {}))["without"],
            "generic_after": city_metrics(after.get(slug, {}))["generic"],
        })
    return {
        "mode": "apply" if apply_changes else "dry_run",
        "coverage_before_json": before_path,
        "coverage_after_json": after_path,
        "cities": cities,
    }


def write_flow_summary(summary: dict[str, Any]) -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / f"address_recovery_flow_{stamp}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)
