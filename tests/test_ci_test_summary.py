import argparse

import allure
import pytest

from scripts.ci_test_summary import parse_junit, render_message
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.integration, pytest.mark.regression]


@scenario("CI-отчёт объясняет нарушение уникальности в базе", epic="Платформа", feature="Инфраструктура и CI", story="Понятная диагностика падения автотеста", severity=allure.severity_level.CRITICAL)
def test_summary_explains_duplicate_database_rows(tmp_path, monkeypatch) -> None:
    with given("JUnit содержит падение MultipleResultsFound с файлом и строкой"):
        report = tmp_path / "report.xml"
        report.write_text(
            """<?xml version="1.0"?>
<testsuites>
  <testsuite name="tests" tests="1" failures="1">
    <testcase classname="tests.test_import_pipeline_foundation" name="test_generated_description_is_reviewable" time="0.2">
      <failure message="sqlalchemy.exc.MultipleResultsFound: Multiple rows were found">tests/test_import_pipeline_foundation.py:74: MultipleResultsFound</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("GITHUB_SHA", "1234567890")

    with when("summary parser формирует уведомление"):
        summary = parse_junit(report)
        message = render_message(summary, argparse.Namespace(
            exit_code=1,
            job_name="Backend",
            run_type="Full Autotests",
            artifact_hint="backend-test-artifacts",
        ))
        allure.attach(message, "Сформированное уведомление", allure.attachment_type.TEXT)

    with then("уведомление содержит человекочитаемое название и причину"):
        assert summary.total == 1
        assert summary.failed == 1
        assert "Generated description is reviewable" in message
        assert "Нарушена уникальность" in message

    with then("уведомление указывает точное место падения без временного суффикса"):
        assert "tests/test_import_pipeline_foundation.py:74" in message
        assert "_new::" not in message
