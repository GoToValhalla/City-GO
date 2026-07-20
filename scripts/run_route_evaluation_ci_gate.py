#!/usr/bin/env python3
"""CITYGO-359: run route evaluation dataset and emit JSON + Markdown reports.

Fails the process only when invariant or deterministic dataset checks fail.
Uses the isolated in-memory SQLite test DB from pytest fixtures — no network.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.route_evaluation.ci_report_plugin import RouteEvaluationReportPlugin

DEFAULT_OUT = ROOT / "artifacts" / "route-evaluation"
TARGET = "tests/route_evaluation"


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    out_dir = Path(args[0]) if args else DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    plugin = RouteEvaluationReportPlugin()
    code = pytest.main(
        [
            TARGET,
            "-q",
            "--no-cov",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
        ],
        plugins=[plugin],
    )

    report = _build_report(plugin, exit_code=int(code))
    json_path = out_dir / "route-evaluation-report.json"
    md_path = out_dir / "route-evaluation-summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown_summary(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 1 if report["failed"] else 0


def _build_report(plugin: RouteEvaluationReportPlugin, *, exit_code: int) -> dict[str, object]:
    failures = [*plugin.invariant_failures, *plugin.other_failures]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": TARGET,
        "passed": plugin.passed,
        "failed": plugin.failed,
        "skipped": plugin.skipped,
        "pytest_exit_code": exit_code,
        "invariant_violation_count": len(plugin.invariant_failures),
        "deterministic_dataset_failure_count": len(plugin.other_failures),
        "failures": failures,
        "status": "failed" if plugin.failed else "passed",
    }


def _markdown_summary(report: dict[str, object]) -> str:
    lines = [
        "# Route Evaluation CI Gate",
        "",
        f"- Status: **{report['status']}**",
        f"- Passed: {report['passed']}",
        f"- Failed: {report['failed']}",
        f"- Skipped: {report['skipped']}",
        f"- Invariant violations: {report['invariant_violation_count']}",
        f"- Deterministic dataset failures: {report['deterministic_dataset_failure_count']}",
        f"- Generated at: {report['generated_at']}",
        "",
    ]
    failures = list(report.get("failures") or [])
    if not failures:
        lines.append("No invariant or dataset failures.")
        lines.append("")
        return "\n".join(lines)
    lines.append("## Failures")
    lines.append("")
    for index, failure in enumerate(failures, 1):
        if not isinstance(failure, dict):
            continue
        lines.append(f"### {index}. {failure.get('violated_invariant') or 'failure'}")
        for key in (
            "scenario_id",
            "entrypoint",
            "build_mode",
            "expected_status",
            "actual_status",
            "violating_place_ids",
            "generation_run_id",
            "nodeid",
            "message",
        ):
            if key in failure and failure[key] not in (None, "", [], {}):
                lines.append(f"- {key}: `{failure[key]}`")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
