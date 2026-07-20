"""CITYGO-359: report builder shapes JSON/Markdown for the CI gate."""

from __future__ import annotations

from scripts.run_route_evaluation_ci_gate import _build_report, _markdown_summary
from tests.route_evaluation.ci_report_plugin import RouteEvaluationReportPlugin


def test_route_evaluation_ci_report_marks_passed_when_clean_new() -> None:
    plugin = RouteEvaluationReportPlugin()
    plugin.passed = 3
    report = _build_report(plugin, exit_code=0)
    assert report["status"] == "passed"
    assert report["failed"] == 0
    assert "No invariant" in _markdown_summary(report)


def test_route_evaluation_ci_report_includes_invariant_failures_new() -> None:
    plugin = RouteEvaluationReportPlugin()
    plugin.failed = 1
    plugin.invariant_failures.append(
        {
            "scenario_id": "single_place",
            "entrypoint": "POST /v1/user-routes/build",
            "build_mode": "auto",
            "violated_invariant": "one_point_never_ready",
            "expected_status": "partial_route",
            "actual_status": "ready",
            "violating_place_ids": ["1"],
        }
    )
    report = _build_report(plugin, exit_code=1)
    md = _markdown_summary(report)
    assert report["status"] == "failed"
    assert report["invariant_violation_count"] == 1
    assert "one_point_never_ready" in md
    assert "single_place" in md
