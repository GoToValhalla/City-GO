"""CITYGO-359: report builder shapes JSON/Markdown for the CI gate."""

from __future__ import annotations

import os

import scripts.run_route_evaluation_ci_gate as ci_gate_module
from scripts.run_route_evaluation_ci_gate import _build_report, _markdown_summary, main
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


def test_route_evaluation_ci_report_fails_on_nonzero_exit_code_even_with_no_test_failures_new() -> None:
    """False-green guard: a pytest usage/collection error (nonzero exit
    code) must never be reported as passed just because zero tests ran
    and therefore zero call-phase failures were recorded."""
    plugin = RouteEvaluationReportPlugin()
    report = _build_report(plugin, exit_code=2)
    assert report["status"] == "failed"
    assert report["failed"] == 0


def test_route_evaluation_ci_gate_main_fails_on_collection_error_new(tmp_path) -> None:
    broken = "tests/route_evaluation/_tmp_broken_collect_new.py"
    with open(broken, "w", encoding="utf-8") as fh:
        fh.write("import nonexistent_module_for_false_green_test\n")
    original_target = ci_gate_module.TARGET
    ci_gate_module.TARGET = broken
    try:
        code = main([str(tmp_path)])
    finally:
        ci_gate_module.TARGET = original_target
        os.remove(broken)
    assert code == 1


def test_route_evaluation_ci_gate_main_fails_on_zero_collected_tests_new(tmp_path) -> None:
    empty_dir = tmp_path / "empty_suite"
    empty_dir.mkdir()
    (empty_dir / "test_nothing.py").write_text("# intentionally no tests\n", encoding="utf-8")
    original_target = ci_gate_module.TARGET
    ci_gate_module.TARGET = str(empty_dir)
    try:
        code = main([str(tmp_path / "out")])
    finally:
        ci_gate_module.TARGET = original_target
    assert code == 1


def test_route_evaluation_ci_gate_main_fails_when_target_does_not_exist_new(tmp_path) -> None:
    original_target = ci_gate_module.TARGET
    ci_gate_module.TARGET = "tests/route_evaluation/_does_not_exist_new"
    try:
        code = main([str(tmp_path)])
    finally:
        ci_gate_module.TARGET = original_target
    assert code == 1
