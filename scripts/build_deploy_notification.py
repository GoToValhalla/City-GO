#!/usr/bin/env python3
"""Build a compact Telegram notification for production deploy workflow."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _status_icon(status: str) -> str:
    return "✅" if status == "success" else "❌" if status in {"failure", "cancelled"} else "⚠️"


def _read_log_summary(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        useful = [line.strip() for line in text.splitlines() if line.strip()]
        if useful:
            lines.append(f"{file_path.name}: {useful[-1]}")
    return lines[-5:]


def build_message(*, build_result: str, deploy_result: str, run_attempt: str, log_dir: Path) -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")
    sha = os.getenv("CITY_GO_DEPLOY_SHA") or os.getenv("GITHUB_SHA", "")
    ref = os.getenv("CITY_GO_DEPLOY_REF") or os.getenv("GITHUB_REF_NAME", "main")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else ""
    status = "success" if build_result == "success" and deploy_result == "success" else "failure"
    lines = [
        f"{_status_icon(status)} CITY GO · PRODUCTION DEPLOY",
        f"Статус: {'прод обновлён' if status == 'success' else 'деплой не прошёл'}",
        f"Прогон: #{run_number or 'unknown'} · попытка {run_attempt}",
        f"Ref: {ref}",
        f"Commit: {sha[:7] if sha else 'unknown'}",
        f"Сборка образов: {_status_icon(build_result)} {build_result}",
        f"Деплой на сервер: {_status_icon(deploy_result)} {deploy_result}",
    ]
    summary = _read_log_summary(log_dir)
    if summary:
        lines.append("Последние строки логов:")
        lines.extend(f"- {item}" for item in summary)
    if run_url:
        lines.append(run_url)
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-result", required=True)
    parser.add_argument("--deploy-result", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, default=Path("/tmp/deploy-log"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        build_message(
            build_result=args.build_result,
            deploy_result=args.deploy_result,
            run_attempt=args.run_attempt,
            log_dir=args.log_dir,
        ),
        encoding="utf-8",
    )
    print(f"deploy_notification_written={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
