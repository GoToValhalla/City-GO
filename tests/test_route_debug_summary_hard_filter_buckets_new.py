from __future__ import annotations

from services.route_pipeline_trace import route_debug_summary


def test_route_debug_summary_exposes_hard_filter_drop_buckets_new() -> None:
    trace = [
        {"stage": "candidate_retrieval", "count": 80},
        {
            "stage": "hard_filter",
            "input_count": 80,
            "kept_count": 0,
            "removed_count": 80,
            "fallback_used": True,
            "reasons": {
                "closed_now": 50,
                "dropped_by_time": 50,
                "avoided_category": 20,
                "dropped_by_exclusion": 20,
                "status": 10,
                "dropped_by_status": 10,
            },
        },
        {"stage": "scoring", "count": 0},
    ]

    summary = route_debug_summary("route-hard-filter-buckets", trace)

    assert summary["death_point"] == "hard_filters"
    assert summary["hard_filters"]["input_count"] == 80
    assert summary["hard_filters"]["output_count"] == 0
    assert summary["hard_filters"]["removed_count"] == 80
    assert summary["hard_filters"]["fallback_used"] is True
    assert summary["hard_filters"]["dropped_by_time"] == 50
    assert summary["hard_filters"]["dropped_by_exclusion"] == 20
    assert summary["hard_filters"]["dropped_by_status"] == 10
    assert summary["hard_filters"]["reason_counts"]["closed_now"] == 50
    assert summary["hard_filters"]["reason_counts"]["avoided_category"] == 20
    assert summary["hard_filters"]["reason_counts"]["status"] == 10
