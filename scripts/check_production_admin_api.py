#!/usr/bin/env python3
"""Check production admin API availability through the public frontend proxy.

The public product can stay healthy while admin-only endpoints fail behind the
same gateway. This script treats any admin 4xx/5xx/timeout as an operations
incident and writes a Telegram-friendly report.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin


@dataclass(frozen=True)
class Check:
    name: str
    path: str
    requires_admin: bool = False


CHECKS = (
    Check("frontend build metadata", "/build.json"),
    Check("backend health through frontend proxy", "/api/health"),
    Check("backend readiness through frontend proxy", "/api/ready"),
    Check("admin cities", "/api/admin/cities?limit=1", requires_admin=True),
    Check("admin verification summary", "/api/admin/place-verifications/summary", requires_admin=True),
    Check("admin data quality summary", "/api/admin/data-quality/summary", requires_admin=True),
)


@dataclass
class Result:
    check: Check
    ok: bool
    status: int | None
    elapsed_ms: int
    detail: str


def normalize_base_url(value: str) -> str:
    base = value.strip().rstrip("/")
    if not base:
        raise ValueError("base URL is empty")
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    return base


def request(check: Check, *, base_url: str, admin_token: str, timeout: float) -> Result:
    started = time.monotonic()
    url = urljoin(f"{base_url}/", check.path.lstrip("/"))
    headers = {"User-Agent": "city-go-admin-api-watchdog/1.0"}
    if check.requires_admin:
        headers["Authorization"] = f"Bearer {admin_token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            status = response.status
            raw = response.read(700).decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as exc:
        raw = exc.read(700).decode("utf-8", errors="replace").strip()
        return Result(
            check=check,
            ok=False,
            status=exc.code,
            elapsed_ms=round((time.monotonic() - started) * 1000),
            detail=raw or exc.reason,
        )
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        return Result(
            check=check,
            ok=False,
            status=None,
            elapsed_ms=round((time.monotonic() - started) * 1000),
            detail=f"{exc.__class__.__name__}: {exc}",
        )

    return Result(
        check=check,
        ok=200 <= status < 300,
        status=status,
        elapsed_ms=round((time.monotonic() - started) * 1000),
        detail=raw[:700],
    )


def status_text(result: Result) -> str:
    status = result.status if result.status is not None else "network"
    mark = "OK" if result.ok else "FAIL"
    line = f"{mark} {result.check.name}: status={status}, {result.elapsed_ms}ms, path={result.check.path}"
    if result.ok:
        return line
    detail = " ".join(result.detail.split())
    if len(detail) > 420:
        detail = f"{detail[:420]}..."
    return f"{line}\n  {detail}"


def build_report(*, base_url: str, results: list[Result]) -> str:
    failed = [result for result in results if not result.ok]
    title = "CITY GO admin API watchdog"
    status = "FAILED" if failed else "OK"
    lines = [
        f"{title}: {status}",
        f"Base URL: {base_url}",
        "",
    ]
    lines.extend(status_text(result) for result in results)
    if failed:
        lines.extend([
            "",
            "Impact: public site may still work, but admin operations are degraded.",
            "Action: open Production Deploy logs and backend/proxy diagnostics; failing paths are listed above.",
        ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("PRODUCTION_BASE_URL", ""))
    parser.add_argument("--admin-token", default=os.getenv("ADMIN_API_TOKEN", ""))
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--output", type=Path, default=Path("admin-api-watchdog.txt"))
    args = parser.parse_args()

    try:
        base_url = normalize_base_url(args.base_url)
    except ValueError as exc:
        args.output.write_text(f"CITY GO admin API watchdog: FAILED\n{exc}\n", encoding="utf-8")
        print(args.output.read_text(encoding="utf-8"), end="")
        return 2

    admin_token = args.admin_token.strip()
    if not admin_token:
        args.output.write_text(
            "CITY GO admin API watchdog: FAILED\nADMIN_API_TOKEN is empty; admin endpoints cannot be checked.\n",
            encoding="utf-8",
        )
        print(args.output.read_text(encoding="utf-8"), end="")
        return 2

    results = [request(check, base_url=base_url, admin_token=admin_token, timeout=args.timeout) for check in CHECKS]
    report = build_report(base_url=base_url, results=results)
    args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 1 if any(not result.ok for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
