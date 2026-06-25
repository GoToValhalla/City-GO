#!/usr/bin/env python3
"""Render actionable CI summaries from pytest and Vitest JUnit XML."""

from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FailedTest:
    classname: str
    name: str
    kind: str
    message: str
    location: str | None = None
    diagnosis: str | None = None
    action: str | None = None


@dataclass
class TestSummary:
    total: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time_seconds: float = 0.0
    failed_tests: list[FailedTest] = field(default_factory=list)
    suite_failures: dict[str, int] = field(default_factory=dict)

    @property
    def failed(self) -> int:
        return self.failures + self.errors

    @property
    def passed(self) -> int:
        return max(0, self.total - self.failed - self.skipped)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


def _safe_float(value: str | None) -> float:
    try:
        return float(value or "0")
    except ValueError:
        return 0.0


def _humanize(value: str) -> str:
    value = value.rsplit(".", 1)[-1]
    value = re.sub(r"^test_", "", value)
    value = re.sub(r"_new$", "", value)
    value = value.replace("_", " ").strip()
    return value[:1].upper() + value[1:] if value else "Неизвестный тест"


def _suite_name(classname: str) -> str:
    module = classname.removeprefix("tests.").removeprefix("src.")
    module = module.split(".")[-1]
    module = re.sub(r"^test_", "", module)
    module = re.sub(r"_new$", "", module)
    return module.replace("_", " ") or "unknown"


def _failure_details(text: str, message: str) -> tuple[str | None, str | None, str | None]:
    combined = f"{message}\n{text}"
    location_match = re.search(r"([\w./-]+\.(?:py|ts|tsx)):(\d+)", combined)
    location = f"{location_match.group(1)}:{location_match.group(2)}" if location_match else None
    rules = [
        ("MultipleResultsFound", "Нарушена уникальность: код ожидал одну запись, но получил несколько.", "Проверить идемпотентность создания записей и уникальный ключ выборки."),
        ("NoResultFound", "Ожидаемая запись не была создана или была отфильтрована.", "Проверить setup теста и условие выборки перед вызовом one()."),
        ("has no attribute", "Тест и реализация рассинхронизированы: тест обращается к удалённому или переименованному API.", "Обновить monkeypatch/import на фактически вызываемую функцию и закрепить контракт тестом."),
        ("Unable to find an element", "Интерфейс не отрендерил ожидаемый элемент либо компонент упал раньше проверки.", "Проверить stderr, обязательные Provider/Router и актуальность пользовательского текста."),
        ("useContext", "React-компонент запущен без обязательного контекстного Provider.", "Обернуть тест в Router/Provider, который используется компонентом в приложении."),
        ("IntegrityError", "База отклонила запись из-за ограничения целостности.", "Проверить уникальные ключи, внешние ключи и очистку данных между тестами."),
        ("AssertionError", "Фактическое поведение не совпало с ожидаемым контрактом теста.", "Сравнить expected/actual в полном логе и определить: регрессия продукта или устаревшее ожидание."),
    ]
    for signature, diagnosis, action in rules:
        if signature in combined:
            return location, diagnosis, action
    return location, "Тест завершился исключением; краткого автоматического диагноза недостаточно.", "Открыть полный traceback в JUnit/Allure и проверить первую строку пользовательского кода."


def parse_junit(path: Path) -> TestSummary:
    summary = TestSummary()
    if not path.exists():
        return summary
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    summary.total = len(cases)
    for case in cases:
        summary.time_seconds += _safe_float(case.attrib.get("time"))
        if case.find("skipped") is not None:
            summary.skipped += 1
            continue
        failure = case.find("failure")
        error = case.find("error")
        node = failure if failure is not None else error
        if node is None:
            continue
        kind = "failure" if failure is not None else "error"
        summary.failures += int(kind == "failure")
        summary.errors += int(kind == "error")
        classname = case.attrib.get("classname", "unknown")
        raw_message = (node.attrib.get("message") or "").strip()
        raw_text = (node.text or "").strip()
        first_line = next((line.strip() for line in (raw_message or raw_text).splitlines() if line.strip()), "")
        message = textwrap.shorten(first_line.replace("\n", " "), width=180, placeholder="…")
        location, diagnosis, action = _failure_details(raw_text, raw_message)
        summary.failed_tests.append(FailedTest(classname, case.attrib.get("name", "unknown"), kind, message, location, diagnosis, action))
        suite = _suite_name(classname)
        summary.suite_failures[suite] = summary.suite_failures.get(suite, 0) + 1
    return summary


def format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = int(seconds % 60)
    return f"{minutes}m {rest}s" if minutes else f"{rest}s"


def progress_bar(rate: float, width: int = 12) -> str:
    filled = round(max(0.0, min(1.0, rate)) * width)
    return "🟩" * filled + "⬜" * (width - filled)


def render_message(summary: TestSummary, args: argparse.Namespace) -> str:
    passed = args.exit_code == 0 and summary.failed == 0
    status_icon = "✅" if passed else "❌"
    status_text = "PASSED" if passed else "FAILED"
    run_url = f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}"
    commit = os.getenv("GITHUB_SHA", "unknown")
    lines = [
        f"{status_icon} City Go {args.job_name} {status_text}",
        f"Прогон: #{os.getenv('GITHUB_RUN_NUMBER', 'unknown')} · попытка {os.getenv('GITHUB_RUN_ATTEMPT', '1')}",
        f"Ветка: {os.getenv('GITHUB_REF_NAME', 'unknown')} · commit {commit[:7] if commit != 'unknown' else commit}",
        "",
        f"Итог: {summary.passed} passed · {summary.failed} failed · {summary.skipped} skipped · {format_duration(summary.time_seconds)}",
        f"Успешность: {summary.pass_rate * 100:.1f}% {progress_bar(summary.pass_rate)}",
    ]
    if summary.suite_failures:
        lines.extend(["", "Затронутые модули:"])
        for suite, count in sorted(summary.suite_failures.items(), key=lambda item: item[1], reverse=True)[:6]:
            lines.append(f"- {suite}: {count}")
    if summary.failed_tests:
        lines.extend(["", "Что именно упало:"])
        for index, failed in enumerate(summary.failed_tests[:4], start=1):
            lines.append(f"{index}. {_humanize(failed.name)}")
            lines.append(f"   Модуль: {_suite_name(failed.classname)}")
            if failed.location:
                lines.append(f"   Место: {failed.location}")
            if failed.message:
                lines.append(f"   Ошибка: {failed.message}")
            if failed.diagnosis:
                lines.append(f"   Причина: {failed.diagnosis}")
            if failed.action:
                lines.append(f"   Действие: {failed.action}")
        if len(summary.failed_tests) > 4:
            lines.append(f"   Ещё падений: {len(summary.failed_tests) - 4}. Полный список в Allure/JUnit.")
    lines.extend(["", f"Артефакты JUnit/Allure: {args.artifact_hint}", f"GitHub: {run_url}"])
    return "\n".join(lines)


def append_step_summary(message: str) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary_file:
            summary_file.write("```text\n" + message + "\n```\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--run-type", required=True)
    parser.add_argument("--artifact-hint", default="uploaded in workflow artifacts")
    parser.add_argument("--exit-code", required=True, type=int)
    args = parser.parse_args()
    summary = parse_junit(args.junit)
    message = render_message(summary, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(message, encoding="utf-8")
    append_step_summary(message)
    print(message)
    return args.exit_code


if __name__ == "__main__":
    sys.exit(main())
