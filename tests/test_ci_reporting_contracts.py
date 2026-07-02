from __future__ import annotations

from pathlib import Path

from scripts.ci_test_summary import _allure_coverage_lines, parse_junit, render_message
from tests.allure_support import citygo_test


@citygo_test("CI summary выводит блок покрытия явными Allure-сценариями")
def test_ci_summary_includes_allure_scenario_coverage(tmp_path, monkeypatch) -> None:
    messages = tmp_path / "artifacts" / "messages"
    messages.mkdir(parents=True)
    (messages / "allure-coverage.txt").write_text(
        "Functional tests: 25\nExplicit Russian scenarios: 13\nCoverage: 52.0%\nIgnored: x\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    lines = _allure_coverage_lines()

    assert "Покрытие явными Allure-сценариями:" in lines
    assert "Functional tests: 25" in lines
    assert "Explicit Russian scenarios: 13" in lines
    assert "Coverage: 52.0%" in lines
    assert "Ignored: x" not in lines


@citygo_test("CI summary парсит JUnit и показывает actionable failure details")
def test_ci_summary_renders_actionable_failure_message(tmp_path, monkeypatch) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
        <testsuite tests="1" failures="1" errors="0" skipped="0" time="1.2">
          <testcase classname="tests.test_admin" name="test_admin_contract" time="1.2">
            <failure message="AssertionError: assert 500 == 200">tests/test_admin.py:42: AssertionError</failure>
          </testcase>
        </testsuite>
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_SHA", "abcdef123456")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")

    summary = parse_junit(junit)
    args = type("Args", (), {"exit_code": 1, "job_name": "Backend full regression", "artifact_hint": "artifact"})()
    message = render_message(summary, args)

    assert "FAILED" in message
    assert "tests/test_admin.py:42" in message
    assert "Фактическое поведение не совпало" in message
    assert "Сравнить expected/actual" in message
