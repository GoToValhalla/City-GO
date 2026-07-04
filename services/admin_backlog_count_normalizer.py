from __future__ import annotations

from typing import Any


def normalize_backlog_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    for queue in payload.get("queues") or []:
        if not isinstance(queue, dict):
            continue
        total = _to_int(queue.get("unique_places_count") or queue.get("total_count"))
        queue["unique_places_count"] = total
        queue["auto_fixable_count"] = min(_to_int(queue.get("auto_fixable_count")), total)
        queue["manual_count"] = min(_to_int(queue.get("manual_count")), total)
        queue["overlap_count"] = min(_to_int(queue.get("overlap_count")), total)
    summary = payload.get("summary") or {}
    if isinstance(summary, dict):
        unique = _to_int(summary.get("unique_problem_places"))
        if unique:
            summary["auto_fixable_places"] = min(_to_int(summary.get("auto_fixable_places")), unique)
            summary["content_gap_places"] = min(_to_int(summary.get("content_gap_places")), unique)
    return payload


def normalize_reduction_plan(plan: dict[str, Any], backlog: dict[str, Any]) -> dict[str, Any]:
    summary = plan.get("summary") or {}
    if not isinstance(summary, dict):
        return plan
    backlog_summary = backlog.get("summary") or {}
    unique = _to_int(backlog_summary.get("unique_problem_places"))
    content = _to_int(backlog_summary.get("content_gap_places"))
    totals = _queue_totals(backlog)
    summary["total_auto_fixable"] = _cap(summary.get("total_auto_fixable"), unique)
    summary["total_manual_after_classification"] = _cap(summary.get("total_manual_after_classification"), totals.get("manual_review", 0))
    summary["route_blockers_reducible"] = _cap(summary.get("route_blockers_reducible"), totals.get("route_blockers", 0))
    summary["unknown_categories_auto_classifiable"] = _cap(summary.get("unknown_categories_auto_classifiable"), totals.get("route_unknown", 0))
    summary["manual_review_reclassifiable"] = _cap(summary.get("manual_review_reclassifiable"), totals.get("manual_review", 0))
    summary["verification_auto_recheckable"] = _cap(summary.get("verification_auto_recheckable"), totals.get("needs_verification", 0))
    summary["content_enrichment_queueable"] = _cap(summary.get("content_enrichment_queueable"), content)
    return plan


def set_would_change(result: Any) -> Any:
    if getattr(result, "dry_run", False) and not getattr(result, "would_change_count", 0):
        result.would_change_count = _to_int(getattr(result, "changed_count", 0))
    return result


def _queue_totals(payload: dict[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for queue in payload.get("queues") or []:
        if isinstance(queue, dict):
            totals[str(queue.get("code") or "")] = _to_int(queue.get("unique_places_count") or queue.get("total_count"))
    return totals


def _cap(value: Any, maximum: int) -> int:
    return max(0, min(_to_int(value), max(0, int(maximum or 0))))


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
