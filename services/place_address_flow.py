"""Оркестратор automatic address recovery flow."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.place_address_coverage_export import export_coverage
from services.place_address_flow_load import city_needs_recovery, load_coverage
from services.place_address_flow_summary import (
    build_flow_summary,
    city_metrics,
    count_apply_skipped,
    write_flow_summary,
)
from services.place_address_recovery import run_recovery_dry_run
from services.place_address_recovery_apply import apply_from_review


def run_address_recovery_flow(
    db: Session,
    *,
    city_slugs: list[str] | None,
    limit: int,
    sleep_seconds: float,
    apply_changes: bool,
    include_generic: bool,
) -> dict[str, Any]:
    before = load_coverage(db, city_slugs)
    before_path = export_coverage(before, label="address_coverage_before")
    city_results = [
        _process_city(db, slug, report, limit, sleep_seconds, apply_changes, include_generic)
        if city_needs_recovery(report, include_generic=include_generic or int(report.get("generic_address_count") or 0) > 0)
        else _skipped_city(slug, report)
        for slug, report in sorted(before.items())
    ]
    after = load_coverage(db, city_slugs)
    after_path = export_coverage(after, label="address_coverage_after")
    summary = build_flow_summary(before, after, city_results, before_path, after_path, apply_changes)
    summary_path = write_flow_summary(summary)
    return {**summary, "summary_json": summary_path}


def _process_city(
    db: Session,
    slug: str,
    before_report: dict[str, Any],
    limit: int,
    sleep_seconds: float,
    apply_changes: bool,
    include_generic: bool,
) -> dict[str, Any]:
    use_generic = include_generic or int(before_report.get("generic_address_count") or 0) > 0
    dry = run_recovery_dry_run(
        db, city_slug=slug, limit=limit, sleep_seconds=sleep_seconds,
        export_review_files=True, include_generic=use_generic,
    )
    files = dry.get("review_files") or {}
    result: dict[str, Any] = {
        "city_slug": slug,
        "checked": dry.get("checked", 0),
        "recoverable": dry.get("recoverable", 0),
        "should_apply": dry.get("should_apply_count", 0),
        "applied": 0,
        "skipped": 0,
        "errors": dry.get("skipped_errors", 0),
        "review_csv": files.get("csv", ""),
        "review_json": files.get("json", ""),
        "apply_result_json": "",
        "reason": "",
        "before": city_metrics(before_report),
    }
    if int(result["should_apply"]) == 0:
        result["reason"] = "no_should_apply_rows"
        return result
    if not apply_changes:
        result["reason"] = "dry_run_only"
        return result
    apply_stats = apply_from_review(db, str(files.get("csv") or ""))
    result["applied"] = apply_stats.get("applied", 0)
    result["skipped"] = count_apply_skipped(apply_stats)
    result["errors"] = apply_stats.get("errors", 0)
    result["apply_result_json"] = apply_stats.get("result_json", "")
    return result


def _skipped_city(slug: str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "city_slug": slug, "checked": 0, "recoverable": 0, "should_apply": 0,
        "applied": 0, "skipped": 0, "errors": 0, "review_csv": "", "review_json": "",
        "apply_result_json": "", "reason": "no_missing_or_generic", "before": city_metrics(report),
    }
