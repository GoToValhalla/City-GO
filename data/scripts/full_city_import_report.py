"""Markdown-отчёт full city import run из JSON снимков и pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_CITIES = (
    "almaty",
    "yerevan",
    "zelenogradsk",
    "kaliningrad",
    "kutaisi",
    "rostov-on-don",
    "khanty-mansiysk",
)
SUSPICIOUS_CATEGORY_MIN = 3


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _city_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["city_slug"]): item for item in snapshot.get("cities", []) if "city_slug" in item}


def _pipeline_by_city(pipeline: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in pipeline.get("results", []):
        grouped.setdefault(str(row.get("city", "")), []).append(row)
    return grouped


def build_report(audit_dir: Path) -> str:
    before = _city_map(_load(audit_dir / "before_snapshot.json"))
    after = _city_map(_load(audit_dir / "after_snapshot.json"))
    pipeline = _load(audit_dir / "pipeline_result.json")
    commit = (audit_dir / "prod_commit.txt").read_text(encoding="utf-8").strip() if (audit_dir / "prod_commit.txt").exists() else "unknown"
    lines = [
        "# Full city import run report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Audit dir: `{audit_dir}`",
        f"Prod commit: `{commit}`",
        "",
        "## City snapshots (before → after)",
        "",
        "| City | total | published | addr+ | photo+ | route_eligible | errors |",
        "|------|------:|----------:|------:|-------:|---------------:|-------:|",
    ]
    for slug in EXPECTED_CITIES:
        prev, curr = before.get(slug, {}), after.get(slug, {})
        if prev.get("error") or curr.get("error"):
            lines.append(f"| {slug} | — | — | — | — | — | city_not_found |")
            continue
        errs = sum(1 for row in _pipeline_by_city(pipeline).get(slug, []) if row.get("status") == "failed")
        lines.append(
            f"| {slug} | {prev.get('places_total', 0)}→{curr.get('places_total', 0)} "
            f"| {prev.get('places_published', 0)}→{curr.get('places_published', 0)} "
            f"| {prev.get('places_with_real_address', 0)}→{curr.get('places_with_real_address', 0)} "
            f"| {prev.get('places_with_public_photo', 0)}→{curr.get('places_with_public_photo', 0)} "
            f"| {prev.get('places_route_eligible', 0)}→{curr.get('places_route_eligible', 0)} "
            f"| {errs} |"
        )
    lines.extend(["", "## Pipeline deltas per city", ""])
    for slug in EXPECTED_CITIES:
        rows = _pipeline_by_city(pipeline).get(slug, [])
        if not rows:
            lines.append(f"- **{slug}**: no pipeline targets executed")
            continue
        created = sum(int((row.get("import_result") or {}).get("created") or 0) for row in rows)
        addr = sum(int((row.get("address_backfill_result") or {}).get("updated") or 0) for row in rows)
        photos = sum(int((row.get("image_enrichment_result") or {}).get("created") or 0) for row in rows)
        lines.append(f"- **{slug}**: OSM created={created}, addresses+={addr}, photos+={photos}")
    lines.extend(["", "## Kaliningrad focus", ""])
    kg = after.get("kaliningrad", before.get("kaliningrad", {}))
    lines.append(f"- places_total={kg.get('places_total', '?')}, published={kg.get('places_published', '?')}")
    lines.append(f"- without_real_address={kg.get('places_without_real_address', '?')}")
    lines.append(f"- category_counts={kg.get('category_counts', {})}")
    lines.extend(["", "## Suspicious category gaps", ""])
    for slug in EXPECTED_CITIES:
        curr = after.get(slug, {})
        low = {cat: count for cat, count in (curr.get("category_counts") or {}).items() if 0 < int(count) < SUSPICIOUS_CATEGORY_MIN}
        if low:
            lines.append(f"- {slug}: {low}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--docs-out", default="docs/routes/full_city_import_run_report.md")
    args = parser.parse_args()
    audit = Path(args.audit_dir)
    text = build_report(audit)
    Path(args.docs_out).write_text(text, encoding="utf-8")
    (audit / "report.md").write_text(text, encoding="utf-8")
    print(text)
