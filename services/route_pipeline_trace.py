from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

_LOGGER = logging.getLogger("city_go.route_pipeline")
_LAST_ROUTE_DEBUG: dict[str, Any] = {}

COUNTER_KEYS = (
    "duration_ms",
    "input_count",
    "output_count",
    "count",
    "kept_count",
    "removed_count",
    "strict_kept_count",
    "relaxed_kept_count",
    "final_candidates_count",
    "raw_candidates_count",
    "after_radius_count",
    "expanded_radius_candidates_count",
    "city_wide_candidates_count",
    "route_visible_candidates_count",
    "places_total_in_city",
    "places_public_catalog",
    "places_route_visible",
    "places_route_eligible",
    "places_with_coords",
    "geo_query_count",
    "candidate_retrieval_expected_count",
    "candidate_retrieval_city_wide_expected_count",
    "target_points",
    "selected_count",
    "selected_count_before_budget",
    "actual_duration_minutes",
    "route_minutes",
    "requested_budget_minutes",
    "hard_budget_minutes",
    "target_minutes",
    "warning_count",
)

STATUS_KEYS = (
    "stage",
    "status",
    "partial_reason",
    "failure_stage",
    "failure_reason",
    "retrieval_strategy_used",
    "fallback_used",
    "fallback_radius_used",
    "fallback_city_wide_used",
    "fallback_route_visible_used",
    "route_quality_status",
    "route_completeness",
    "expansion_level",
    "fallback_level",
    "user_explanation",
)

IMPORTANT_KEYS = (
    "city_id",
    "input_city_id",
    "city_slug",
    "city_db_id",
    "start_point",
    "center_used",
    "radius_meters",
    "requested_radius_meters",
    "route_time_mode",
    "time_of_day",
    "interests",
    "avoided_categories",
    "excluded_place_ids",
    "warnings",
    "reasons",
    "removal_reasons",
    "strict_removal_reasons",
    "relaxed_removal_reasons",
    "failed_gates",
    "retrieval_loss_summary",
    "spatial_density",
    "retrieval_counts",
    "final_candidate_categories",
    "sample_candidate_ids",
    "final_place_ids",
)

SAMPLE_LIST_KEYS = {
    "sample_candidates",
    "kept_sample",
    "rejected_sample",
    "top_scored_candidates",
    "final_points",
    "route_sample",
    "final_route_sample",
    "candidate_options",
}


@dataclass
class RoutePipelineTrace:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, stage: str, **payload: Any) -> None:
        self.entries.append({"stage": stage, **payload})

    def snapshot(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.entries]


def top_scores(scored: list[object], limit: int = 3) -> list[float]:
    return [round(float(getattr(item, "score", 0.0) or 0.0), 4) for item in scored[:limit]]


def timed_trace(trace: RoutePipelineTrace, stage: str, started: float, **payload: Any) -> None:
    trace.add(stage, duration_ms=int((perf_counter() - started) * 1000), **payload)


def compact_route_trace(trace: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return a phone-copyable trace without huge nested candidate payloads."""
    return [_compact_entry(entry) for entry in list(trace or [])]


def route_debug_summary(route_id: str, trace: list[dict[str, Any]] | None) -> dict[str, Any]:
    entries = list(trace or [])
    by_stage = {str(entry.get("stage")): entry for entry in entries if entry.get("stage")}
    retrieval = by_stage.get("retrieval") or by_stage.get("candidate_retrieval") or {}
    candidate_retrieval = by_stage.get("candidate_retrieval") or {}
    hard_filter = by_stage.get("hard_filters") or by_stage.get("hard_filter") or {}
    scoring = by_stage.get("scoring") or by_stage.get("scoring_raw") or {}
    assembly = by_stage.get("assembly") or {}
    budget_fit = by_stage.get("budget_fit") or {}
    final = by_stage.get("final") or {}
    return {
        "route_id": route_id,
        "failure_stage": final.get("failure_stage") or _first_zero_stage(entries),
        "retrieval": {
            "final_candidates_count": _pick_number(retrieval, "final_candidates_count", "count"),
            "raw_candidates_count": _pick_number(retrieval, "raw_candidates_count"),
            "after_radius_count": _pick_number(retrieval, "after_radius_count"),
            "expanded_radius_candidates_count": _pick_number(retrieval, "expanded_radius_candidates_count"),
            "city_wide_candidates_count": _pick_number(retrieval, "city_wide_candidates_count"),
            "route_visible_candidates_count": _pick_number(retrieval, "route_visible_candidates_count"),
            "strategy": retrieval.get("retrieval_strategy_used"),
            "fallback_radius_used": retrieval.get("fallback_radius_used"),
            "fallback_city_wide_used": retrieval.get("fallback_city_wide_used"),
            "fallback_route_visible_used": retrieval.get("fallback_route_visible_used"),
        },
        "city": {
            "places_total_in_city": candidate_retrieval.get("places_total_in_city") or retrieval.get("places_total_in_city"),
            "places_public_catalog": candidate_retrieval.get("places_public_catalog") or retrieval.get("after_public_catalog_count"),
            "places_route_visible": candidate_retrieval.get("places_route_visible"),
            "places_route_eligible": candidate_retrieval.get("places_route_eligible") or retrieval.get("after_route_eligible_count"),
            "geo_query_count": candidate_retrieval.get("geo_query_count"),
        },
        "pipeline_counts": {
            "hard_filter_input": hard_filter.get("input_count"),
            "hard_filter_output": hard_filter.get("output_count") or hard_filter.get("kept_count"),
            "scoring_output": scoring.get("output_count") or scoring.get("count"),
            "assembly_output": assembly.get("selected_count"),
            "budget_fit_output": budget_fit.get("output_count") or budget_fit.get("kept_count"),
            "final_points": final.get("final_points_count"),
        },
        "important": {
            "partial_reason": final.get("partial_reason"),
            "warnings": _collect_warnings(entries),
            "sample_candidate_ids": retrieval.get("sample_candidate_ids"),
            "retrieval_loss_summary": retrieval.get("retrieval_loss_summary"),
        },
    }


def log_route_trace(route_id: str, trace: RoutePipelineTrace) -> None:
    full_trace = trace.snapshot()
    compact = compact_route_trace(full_trace)
    summary = route_debug_summary(route_id, full_trace)
    global _LAST_ROUTE_DEBUG
    _LAST_ROUTE_DEBUG = {
        "route_id": route_id,
        "summary": summary,
        "compact_trace": compact,
        "full_trace": deepcopy(_json_safe(full_trace)),
    }
    _LOGGER.info(json.dumps({"route_id": route_id, "summary": summary, "trace": compact}, ensure_ascii=False, sort_keys=True))


def get_last_route_debug() -> dict[str, Any]:
    return deepcopy(_LAST_ROUTE_DEBUG)


def _compact_entry(entry: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in (*STATUS_KEYS, *COUNTER_KEYS, *IMPORTANT_KEYS):
        if key in entry:
            result[key] = _compact_value(entry[key])
    for key in SAMPLE_LIST_KEYS:
        if key in entry:
            result[key] = _compact_sample(entry[key])
    return result


def _compact_value(value: Any) -> Any:
    if isinstance(value, list):
        if all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
            return value[:20]
        return _compact_sample(value)
    if isinstance(value, dict):
        return {str(key): _compact_value(val) for key, val in list(value.items())[:40]}
    return _json_safe(value)


def _compact_sample(value: Any, limit: int = 8) -> list[Any]:
    rows = list(value or []) if isinstance(value, list) else []
    compact_rows: list[Any] = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            compact_rows.append({
                key: row.get(key)
                for key in ("id", "place_id", "name", "title", "category", "reason", "score", "distance_meters")
                if key in row
            })
        else:
            compact_rows.append(_json_safe(row))
    return compact_rows


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _json_safe(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        return str(value)


def _pick_number(payload: dict[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return value
    return None


def _first_zero_stage(entries: list[dict[str, Any]]) -> str | None:
    for entry in entries:
        stage = str(entry.get("stage") or "")
        output = entry.get("output_count", entry.get("count", entry.get("kept_count")))
        if stage and output == 0:
            return stage
    return None


def _collect_warnings(entries: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for entry in entries:
        for warning in list(entry.get("warnings") or []):
            if isinstance(warning, str) and warning not in warnings:
                warnings.append(warning)
        if len(warnings) >= 20:
            break
    return warnings
