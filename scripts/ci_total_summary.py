#!/usr/bin/env python3
"""Build one readable CI report from backend/frontend JUnit and Allure results."""

from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from scripts.ci_test_summary import _failure_details, format_duration
except ModuleNotFoundError:  # Running as python scripts/ci_total_summary.py.
    from ci_test_summary import _failure_details, format_duration


@dataclass
class TestCaseResult:
    source: str
    classname: str
    name: str
    title: str
    test_type: str
    functional_group: str
    duration: float
    status: str
    message: str = ""
    location: str | None = None
    diagnosis: str | None = None
    action: str | None = None
    failed_step: str | None = None


@dataclass
class GroupStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def add(self, case: TestCaseResult) -> None:
        self.total += 1
        if case.status == "passed":
            self.passed += 1
        elif case.status == "skipped":
            self.skipped += 1
        else:
            self.failed += 1


@dataclass
class TotalReport:
    cases: list[TestCaseResult] = field(default_factory=list)
    stages: dict[str, str] = field(default_factory=dict)

    @property
    def stats(self) -> GroupStats:
        result = GroupStats()
        for case in self.cases:
            result.add(case)
        return result

    @property
    def duration(self) -> float:
        return sum(case.duration for case in self.cases)

    @property
    def failed_cases(self) -> list[TestCaseResult]:
        return [case for case in self.cases if case.status == "failed"]

    @property
    def failed_stages(self) -> list[str]:
        return [name for name, status in self.stages.items() if status not in {"success", "skipped"}]

    @property
    def successful(self) -> bool:
        return not self.failed_cases and not self.failed_stages


TYPE_ORDER = ("Unit", "API", "Integration", "UI")
FUNCTION_ORDER = (
    "Импорт и обогащение",
    "Категории и taxonomy",
    "Качество и проверка данных",
    "Построение и прохождение маршрута",
    "Каталог мест",
    "Админка",
    "Города и регионы",
    "Telegram",
    "Пользователи",
    "Инфраструктура и CI",
)


def _safe_float(value: str | None) -> float:
    try:
        return float(value or "0")
    except ValueError:
        return 0.0


def _properties(case: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    properties = case.find("properties")
    if properties is None:
        return result
    for node in properties.findall("property"):
        name = node.attrib.get("name")
        if name:
            result[name] = node.attrib.get("value", node.text or "")
    return result


def _fallback_title(name: str) -> str:
    value = re.sub(r"^test_", "", name)
    value = re.sub(r"_new$", "", value)
    value = value.replace("_", " ").strip()
    return value[:1].upper() + value[1:] if value else "Неизвестный тест"


def _frontend_type(classname: str, name: str) -> str:
    text = f"{classname} {name}".lower()
    if any(token in text for token in ("/api/", ".api.", "contract", "endpoint")):
        return "API"
    if any(token in text for token in ("integration", "e2e", "playwright")):
        return "Integration"
    if any(token in text for token in (".tsx", "page", "component", "widget", "layout", "render")):
        return "UI"
    return "Unit"


def _functional_group(text: str) -> str:
    value = text.lower()
    rules = (
        (("import", "enrichment", "source_", "pipeline"), "Импорт и обогащение"),
        (("taxonomy", "category"), "Категории и taxonomy"),
        (("quality", "verification", "review", "conflict"), "Качество и проверка данных"),
        (("route", "navigation", "recommendation", "draft"), "Построение и прохождение маршрута"),
        (("admin",), "Админка"),
        (("place", "nearby", "open_now", "map"), "Каталог мест"),
        (("city", "destination", "region"), "Города и регионы"),
        (("telegram", "miniapp", "mini_app"), "Telegram"),
        (("user", "profile", "auth", "signal"), "Пользователи"),
        (("ci_", "health", "deploy", "readiness"), "Инфраструктура и CI"),
    )
    for tokens, group in rules:
        if any(token in value for token in tokens):
            return group
    return "Прочее"


def parse_junit(path: Path | None, source: str) -> list[TestCaseResult]:
    if path is None or not path.exists():
        return []
    root = ET.parse(path).getroot()
    results: list[TestCaseResult] = []
    for case in root.iter("testcase"):
        props = _properties(case)
        classname = case.attrib.get("classname", "unknown")
        name = case.attrib.get("name", "unknown")
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        node = failure if failure is not None else error
        status = "skipped" if skipped is not None else "failed" if node is not None else "passed"
        message = ""
        location = diagnosis = action = None
        if node is not None:
            raw_message = (node.attrib.get("message") or "").strip()
            raw_text = (node.text or "").strip()
            first_line = next((line.strip() for line in (raw_message or raw_text).splitlines() if line.strip()), "")
            message = textwrap.shorten(first_line.replace("\n", " "), width=200, placeholder="…")
            location, diagnosis, action = _failure_details(raw_text, raw_message)
        test_type = props.get("test_type") or (_frontend_type(classname, name) if source == "frontend" else "Unit")
        functional_group = props.get("functional_group") or _functional_group(f"{classname} {name}")
        results.append(TestCaseResult(
            source=source,
            classname=classname,
            name=name,
            title=props.get("display_title") or _fallback_title(name),
            test_type=test_type,
            functional_group=functional_group,
            duration=_safe_float(case.attrib.get("time")),
            status=status,
            message=message,
            location=location,
            diagnosis=diagnosis,
            action=action,
        ))
    return results


def _failed_step(steps: Iterable[dict], parents: tuple[str, ...] = ()) -> str | None:
    for step in steps:
        name = str(step.get("name") or "Неименованный шаг")
        path = (*parents, name)
        nested = _failed_step(step.get("steps") or [], path)
        if nested:
            return nested
        if step.get("status") in {"failed", "broken"}:
            return " → ".join(path)
    return None


def _allure_records(directory: Path | None) -> list[dict]:
    if directory is None or not directory.exists():
        return []
    records: list[dict] = []
    for path in directory.rglob("*-result.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        labels = {label.get("name"): label.get("value") for label in data.get("labels", []) if label.get("name")}
        records.append({
            "name": data.get("name") or "",
            "full_name": data.get("fullName") or "",
            "node_id": labels.get("node_id") or "",
            "feature": labels.get("feature") or labels.get("suite") or "",
            "failed_phase": labels.get("failed_phase") or "",
            "failed_step": _failed_step(data.get("steps") or []),
            "status": data.get("status") or "",
        })
    return records


def _matches_allure(case: TestCaseResult, record: dict) -> bool:
    if case.name and case.name in {record["name"], record["full_name"].rsplit("#", 1)[-1]}:
        return True
    node_id = record["node_id"]
    if node_id and (node_id.endswith(f"::{case.name}") or case.name in node_id):
        return True
    dotted = f"{case.classname}.{case.name}"
    return bool(record["full_name"] and (record["full_name"] == dotted or record["full_name"].endswith(f".{case.name}")))


def enrich_with_allure(cases: list[TestCaseResult], directory: Path | None) -> None:
    records = _allure_records(directory)
    for case in cases:
        if case.source != "backend" or case.status != "failed":
            continue
        record = next((item for item in records if item["status"] in {"failed", "broken"} and _matches_allure(case, item)), None)
        if not record:
            case.failed_step = "Выполнение проверки"
            continue
        case.title = record["name"] or case.title
        case.functional_group = record["feature"] or case.functional_group
        case.failed_step = record["failed_step"] or record["failed_phase"] or "Выполнение проверки"


def read_stages(path: Path | None, backend_status: str, frontend_status: str) -> dict[str, str]:
    stages = {"Backend tests": backend_status, "Frontend job": frontend_status}
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        stages.pop("Frontend job", None)
        stages.update({
            "Frontend lint": str(data.get("lint", frontend_status)),
            "Frontend tests": str(data.get("tests", frontend_status)),
            "Frontend build": str(data.get("build", frontend_status)),
        })
    return stages


def _grouped(cases: list[TestCaseResult], attribute: str) -> dict[str, GroupStats]:
    groups: dict[str, GroupStats] = defaultdict(GroupStats)
    for case in cases:
        groups[getattr(case, attribute)].add(case)
    return dict(groups)


def _stats_line(label: str, stats: GroupStats) -> str:
    details = [f"{stats.passed}/{stats.total}"]
    if stats.failed:
        details.append(f"упало {stats.failed}")
    if stats.skipped:
        details.append(f"пропущено {stats.skipped}")
    return f"{label}: " + " · ".join(details)


def _stage_icon(status: str) -> str:
    return "✅" if status == "success" else "⏭" if status == "skipped" else "❌"


def render_report(report: TotalReport) -> str:
    stats = report.stats
    run_number = os.getenv("GITHUB_RUN_NUMBER", "unknown")
    branch = os.getenv("GITHUB_REF_NAME", "unknown")
    commit = os.getenv("GITHUB_SHA", "unknown")[:7]
    run_url = f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}"

    if report.successful:
        return "\n".join([
            f"CITY GO CI #{run_number}: passed",
            f"{stats.passed}/{stats.total} tests passed · {format_duration(report.duration)}",
            f"{branch} · {commit}",
            run_url,
        ])

    failed_stages = ", ".join(report.failed_stages) or "unknown stage"
    lines = [
        f"CITY GO · CI #{run_number}",
        "Статус: не пройден",
        f"Тесты: {stats.failed} из {stats.total} упали · {format_duration(report.duration)}",
        f"Этапы: {failed_stages}",
    ]
    if report.failed_cases:
        lines.append("Первые причины:")
        for case in report.failed_cases[:3]:
            where = f" ({case.location})" if case.location else ""
            detail = case.message or case.title
            lines.append(f"- {case.name}{where}: {detail}")
        remaining = len(report.failed_cases) - 3
        if remaining > 0:
            lines.append(f"+ ещё {remaining}; полный список в GitHub.")
    lines.extend([f"{branch} · {commit}", run_url])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-junit", type=Path)
    parser.add_argument("--frontend-junit", type=Path)
    parser.add_argument("--backend-allure-dir", type=Path)
    parser.add_argument("--frontend-stages", type=Path)
    parser.add_argument("--backend-status", default="unknown")
    parser.add_argument("--frontend-status", default="unknown")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cases = parse_junit(args.backend_junit, "backend") + parse_junit(args.frontend_junit, "frontend")
    enrich_with_allure(cases, args.backend_allure_dir)
    report = TotalReport(
        cases=cases,
        stages=read_stages(args.frontend_stages, args.backend_status, args.frontend_status),
    )
    message = render_report(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(message, encoding="utf-8")
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
