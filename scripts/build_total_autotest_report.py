#!/usr/bin/env python3
"""Build a compact Telegram report from per-job CI summary artifacts only."""

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


def _read_messages(messages_dir: Path) -> list[str]:
    messages: list[tuple[str, str]] = []
    if not messages_dir.exists():
        return []
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
    return [text for _, text in sorted(messages, key=lambda item: SUMMARY_ORDER.get(item[0], 99))]


def build_report(messages_dir: Path) -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")
    sha = os.getenv("GITHUB_SHA", "")
    ref = os.getenv("GITHUB_REF_NAME", "main")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else ""
    messages = _read_messages(messages_dir)
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
