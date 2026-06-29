#!/usr/bin/env python3
"""Print compact key=value import job summaries from admin JSON."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any

TOP_KEYS = (
    "current_step launch_status can_run can_retry can_cancel can_publish "
    "can_unpublish places_total places_published places_unpublished places_found "
    "places_saved scopes_total scopes_succeeded failed_items last_error"
).split()
DIFF_KEYS = (
    "created updated unchanged rejected hidden needs_review meaningful_changes "
    "missing_from_source"
).split()

def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first(payload: Mapping[str, Any], keys: Sequence[str], default: Any = "") -> Any:
    return next((payload[key] for key in keys if payload.get(key) is not None), default)


def _clean(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return " ".join(str(value).split())


def _details(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(payload.get("step_details"))

def _diff(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    details = _details(payload)
    return _mapping(
        details.get("import_diff")
        or details.get("import_summary")
        or payload.get("import_diff")
        or payload.get("import_summary")
    )

def _changed_count(payload: Mapping[str, Any], diff: Mapping[str, Any]) -> Any:
    direct = _first(diff, ("changed_place_ids_count", "changed_ids_count"), None)
    if direct is not None:
        return direct
    ids = _first(_details(payload), ("changed_place_ids",), diff.get("changed_place_ids"))
    return len(ids) if isinstance(ids, Sequence) and not isinstance(ids, str | bytes) else 0

def _readiness(payload: Mapping[str, Any]) -> Any:
    details = _details(payload)
    pipeline = _mapping(details.get("unified_pipeline"))
    return _first(payload, ("readiness_score",), _first(details, ("readiness_score",), pipeline.get("readiness_score", "")))

def _warnings(payload: Mapping[str, Any]) -> list[Any]:
    raw = _details(payload).get("warnings", [])
    return list(raw) if isinstance(raw, Sequence) and not isinstance(raw, str | bytes) else []

def build_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    diff = _diff(payload)
    summary = {
        "job_status": _first(payload, ("status", "job_status")),
        "city_active": _first(payload, ("is_city_active", "city_active")),
        "readiness_score": _readiness(payload),
        "changed_place_ids_count": _changed_count(payload, diff),
        "warnings_count": len(_warnings(payload)),
        "warning_1_step": "",
        "warning_1_error": "",
    }
    summary.update({key: payload.get(key, "") for key in TOP_KEYS})
    summary.update({key: diff.get(key, 0) for key in DIFF_KEYS})
    return summary

def _warning_item(index_item: tuple[int, Any]) -> dict[str, Any]:
    index, item = index_item
    data = _mapping(item)
    error = data.get("error") or data.get("message") or data.get("detail") or (item if isinstance(item, str) else "")
    return {f"warning_{index}_step": data.get("step", ""), f"warning_{index}_error": error}

def _warning_lines(warnings: Sequence[Any]) -> dict[str, Any]:
    return {key: value for item in map(_warning_item, enumerate(warnings, start=1)) for key, value in item.items()}

def main() -> int:
    payload = _mapping(json.load(sys.stdin))
    summary = {**build_summary(payload), **_warning_lines(_warnings(payload))}
    sys.stdout.write("".join(f"{key}={_clean(value)}\n" for key, value in summary.items()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
