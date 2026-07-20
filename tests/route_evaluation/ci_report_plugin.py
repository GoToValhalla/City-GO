"""Pytest plugin: collect route-evaluation FailureRecords for CI artifacts."""

from __future__ import annotations

from typing import Any

import pytest

from tests.route_evaluation.invariants import RouteInvariantViolation


class RouteEvaluationReportPlugin:
    """Accumulates invariant failures and plain assertion failures."""

    def __init__(self) -> None:
        self.invariant_failures: list[dict[str, object]] = []
        self.other_failures: list[dict[str, object]] = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: Any, call: Any) -> Any:
        outcome = yield
        report = outcome.get_result()
        if report.when != "call":
            return
        if report.passed:
            self.passed += 1
            return
        if report.skipped:
            self.skipped += 1
            return
        if not report.failed:
            return
        self.failed += 1
        excinfo = getattr(call, "excinfo", None)
        if excinfo is not None and excinfo.errisinstance(RouteInvariantViolation):
            self.invariant_failures.append(excinfo.value.record.as_dict())
            return
        self.other_failures.append(
            {
                "nodeid": str(getattr(report, "nodeid", "")),
                "violated_invariant": "deterministic_dataset_failure",
                "message": str(getattr(report, "longrepr", ""))[:2000],
            }
        )
