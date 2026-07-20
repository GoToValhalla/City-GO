#!/usr/bin/env python3
"""Build a compact Telegram notification for production deploy workflow.

Root cause this fixes: the previous _read_log_summary picked the LAST
non-empty line of each artifact log file, sorted alphabetically by
filename — a file with no real error (e.g. ssh-keyscan.log, whose last line
is routinely just a success message) could push out the file that actually
contains the failure, and even the right file's last line is often a
routine status line ("=== Docker compose status after deploy up ===" /
"docker compose ps" output), not the ERROR that explains what broke. The
notification therefore often showed noise instead of the real failure
reason and never named which deploy stage failed.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

# Maps an artifact log filename to a short, human-readable deploy stage
# name so a failed run can be attributed to a stage without reading the
# full workflow. Order matters only for iteration below; lookup is by key.
_STAGE_NAMES: dict[str, str] = {
    "ssh-keyscan.log": "SSH preflight",
    "ssh-preflight-warning.log": "SSH preflight",
    "deploy-on-server.log": "Деплой на сервер (docker load/compose up)",
    "verify-build-json.log": "Проверка build.json",
    "verify-backend-ready.log": "Проверка готовности backend",
}

_ERROR_LINE_RE = re.compile(r"(ERROR:|Traceback|FAILED|Deploy blocked)", re.IGNORECASE)


def _status_icon(status: str) -> str:
    return "✅" if status == "success" else "❌" if status in {"failure", "cancelled"} else "⚠️"


def _stage_name(file_path: Path) -> str:
    return _STAGE_NAMES.get(file_path.name, file_path.name)


def _error_lines(text: str, *, limit: int = 3) -> list[str]:
    """Real error lines only — never a routine status/progress line. A file
    with no line matching _ERROR_LINE_RE contributes nothing, rather than
    falling back to its last line (which is what produced noise before)."""
    matches = [line.strip() for line in text.splitlines() if _ERROR_LINE_RE.search(line)]
    # Keep the first occurrences: the earliest ERROR in a log is normally
    # the root cause; later ones are often the same failure re-logged by an
    # outer `exit "$STATUS"` handler restating it.
    return matches[:limit]


def _failed_stage_summary(log_dir: Path) -> list[str]:
    if not log_dir.exists():
        return []
    lines: list[str] = []
    for file_path in sorted(log_dir.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        errors = _error_lines(text)
        if not errors:
            continue
        stage = _stage_name(file_path)
        lines.append(f"[{stage}]")
        lines.extend(f"  {line}" for line in errors)
    return lines


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
    if status != "success":
        errors = _failed_stage_summary(log_dir)
        if errors:
            lines.append("Причина сбоя (реальные ERROR-строки из логов деплоя):")
            lines.extend(errors)
        else:
            lines.append(
                "Реальные ERROR-строки не найдены в артефакте логов — см. полный лог в run/artifacts."
            )
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
