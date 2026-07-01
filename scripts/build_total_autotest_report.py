#!/usr/bin/env python3
"""Build a compact Telegram report from per-job CI summary artifacts and job results."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

SUMMARY_ORDER = {
    "backend.txt": 0,
    "backend-coverage.txt": 1,
    "frontend.txt": 2,
    "frontend-coverage.txt": 3,
}
SUMMARY_NAMES = set(SUMMARY_ORDER)
REQUIRED_JOBS = {
    "backend": "BACKEND_JOB_RESULT",
    "frontend": "FRONTEND_JOB_RESULT",
}


def _read_messages(messages_dir: Path) -> dict[str, str]:
    messages: list[tuple[str, str]] = []
    if not messages_dir.exists():
        return {}
    for path in sorted(messages_dir.rglob("*.txt")):
        if path.name not in SUMMARY_NAMES:
            continue
        if "artifacts/messages" not in path.as_posix():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if text:
            messages.append((path.name, text))
    return {name: text for name, text in sorted(messages, key=lambda item: SUMMARY_ORDER.get(item[0], 99))}


def _job_failure_messages(messages: dict[str, str]) -> list[str]:
    failures: list[str] = []
    for label, env_name in REQUIRED_JOBS.items():
        result = os.getenv(env_name, "unknown")
        if result in {"success", "skipped"}:
            continue
        summary_name = f"{label}.txt"
        if summary_name in messages:
            continue
        failures.append(
            f"❌ City Go {label.capitalize()} job FAILED\n"
            f"Статус job: {result}. Summary artifact `{summary_name}` не создан. "
            "Откройте job logs: падение произошло до формирования отчёта."
        )
    return failures


def build_report(messages_dir: Path) -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")
    sha = os.getenv("GITHUB_SHA", "")
    ref = os.getenv("GITHUB_REF_NAME", "main")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else ""
    messages_by_name = _read_messages(messages_dir)
    messages = [messages_by_name[name] for name in sorted(messages_by_name, key=lambda key: SUMMARY_ORDER.get(key, 99))]
    messages.extend(_job_failure_messages(messages_by_name))
    failed = any(message.startswith("❌") for message in messages)
    lines = [
        "❌ CITY GO · CI" if failed else "✅ CITY GO · CI",
        "Статус: не пройден" if failed else "Статус: пройден",
        f"Прогон: #{run_number or 'unknown'}",
        f"Ref: {ref}",
        f"Commit: {sha[:7] if sha else 'unknown'}",
    ]
    if messages:
        lines.append("")
        lines.extend(messages)
    else:
        lines.append("Нет backend/frontend/coverage summary artifacts. Проверьте backend/frontend jobs.")
    if run_url:
        lines.append("")
        lines.append(run_url)
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(args.messages_dir), encoding="utf-8")
    print(f"total_autotest_report_written={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
