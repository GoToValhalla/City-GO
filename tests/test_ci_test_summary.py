import argparse

from scripts.ci_test_summary import parse_junit, render_message


def test_summary_explains_duplicate_database_rows(tmp_path, monkeypatch) -> None:
    report = tmp_path / "report.xml"
    report.write_text(
        """<?xml version="1.0"?>
<testsuites>
  <testsuite name="tests" tests="1" failures="1">
    <testcase classname="tests.test_import_pipeline_foundation_new" name="test_ai_description_is_not_mocked_or_high_confidence_new" time="0.2">
      <failure message="sqlalchemy.exc.MultipleResultsFound: Multiple rows were found">tests/test_import_pipeline_foundation_new.py:74: MultipleResultsFound</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_SHA", "1234567890")
    summary = parse_junit(report)
    message = render_message(summary, argparse.Namespace(
        exit_code=1,
        job_name="Backend",
        run_type="Full Autotests",
        artifact_hint="backend-test-artifacts",
    ))

    assert summary.total == 1
    assert summary.failed == 1
    assert "Ai description is not mocked or high confidence" in message
    assert "Нарушена уникальность" in message
    assert "tests/test_import_pipeline_foundation_new.py:74" in message
    assert "_new::" not in message
