#!/usr/bin/env python3
"""Production smoke checks for City GO post-deploy verification.

The script intentionally prints a compact, safe summary. It does not include response bodies
from authenticated admin endpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_PUBLIC_CHECKS: tuple[tuple[str, str], ...] = (
    ("build", "/build.json"),
    ("backend_ready", "/ready"),
    ("frontend", "/"),
)

DEFAULT_ADMIN_CHECKS: tuple[tuple[str, str], ...] = (
    ("admin_system_health", "/admin/system-health"),
    ("admin_quality", "/admin/quality"),
    ("admin_taxonomy_categories", "/admin/taxonomy/categories?limit=1"),
)

ROUTE_SMOKE_PATH = "/v1/user-routes/build"


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    method: str
    path: str
    expected_statuses: tuple[int, ...] = (200,)
    admin: bool = False
    body: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SmokeResult:
    name: str
    status: str
    detail: str = ""
    http_status: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class ProductionSmokeConfig:
    base_url: str
    expected_sha: str = ""
    admin_token: str = ""
    route_smoke_enabled: bool = False
    route_city_id: str = ""
    route_lat: float | None = None
    route_lng: float | None = None


def normalize_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    if not url:
        raise ValueError("PRODUCTION_BASE_URL is required")
    if not url.startswith(("http://", "https://")):
        raise ValueError("PRODUCTION_BASE_URL must start with http:// or https://")
    return url


def build_default_checks(config: ProductionSmokeConfig) -> list[SmokeCheck]:
    checks = [SmokeCheck(name=name, method="GET", path=path) for name, path in DEFAULT_PUBLIC_CHECKS]
    if config.admin_token:
        checks.extend(SmokeCheck(name=name, method="GET", path=path, admin=True) for name, path in DEFAULT_ADMIN_CHECKS)
    if config.route_smoke_enabled:
        checks.append(_route_smoke_check(config))
    return checks


def run_smoke(config: ProductionSmokeConfig, checks: Sequence[SmokeCheck] | None = None) -> list[SmokeResult]:
    selected_checks = list(checks or build_default_checks(config))
    results: list[SmokeResult] = []
    for check in selected_checks:
        result = execute_check(config, check)
        if result.ok and check.name == "build" and config.expected_sha:
            result = validate_build_sha(result, config.expected_sha)
        results.append(result)
    return results


def execute_check(config: ProductionSmokeConfig, check: SmokeCheck) -> SmokeResult:
    headers = {"User-Agent": "city-go-production-smoke/1.0"}
    if check.admin:
        if not config.admin_token:
            return SmokeResult(check.name, "skipped", "admin token is missing")
        headers["Authorization"] = f"Bearer {config.admin_token}"
    data = None
    if check.body is not None:
        data = json.dumps(check.body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    url = build_url(config.base_url, check.path)
    request = urllib.request.Request(url, data=data, headers=headers, method=check.method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            raw = response.read(256_000).decode("utf-8", errors="replace")
            http_status = int(response.status)
    except urllib.error.HTTPError as exc:
        return SmokeResult(check.name, "failed", f"http_{exc.code}", exc.code)
    except (OSError, urllib.error.URLError) as exc:
        return SmokeResult(check.name, "failed", exc.__class__.__name__)

    if http_status not in check.expected_statuses:
        return SmokeResult(check.name, "failed", f"unexpected_http_{http_status}", http_status)
    if check.name == "build":
        return SmokeResult(check.name, "ok", safe_build_detail(raw), http_status)
    if check.name == "route_quick":
        return validate_route_response(raw, http_status)
    return SmokeResult(check.name, "ok", f"http_{http_status}", http_status)


def build_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{normalize_base_url(base_url)}/{path.lstrip('/')}"


def safe_build_detail(raw: str) -> str:
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        return "invalid_json"
    sha = str(payload.get("sha") or payload.get("commit") or "")[:7]
    return f"sha_{sha}" if sha else "sha_missing"


def validate_build_sha(result: SmokeResult, expected_sha: str) -> SmokeResult:
    expected = expected_sha[:7]
    actual = result.detail.removeprefix("sha_")
    if actual == expected:
        return result
    return SmokeResult(result.name, "failed", f"expected_{expected}_got_{actual}", result.http_status)


def validate_route_response(raw: str, http_status: int) -> SmokeResult:
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        return SmokeResult("route_quick", "failed", "invalid_json", http_status)
    total_places = int(payload.get("total_places") or len(payload.get("points") or []))
    status = str(payload.get("status") or "")
    if status in {"failed", "empty", "preview_failed"}:
        return SmokeResult("route_quick", "failed", f"status_{status}", http_status)
    if total_places < 2:
        return SmokeResult("route_quick", "failed", f"expected_min_2_points_got_{total_places}", http_status)
    return SmokeResult("route_quick", "ok", f"points_{total_places}", http_status)


def _route_smoke_check(config: ProductionSmokeConfig) -> SmokeCheck:
    if not config.route_city_id:
        raise ValueError("CITY_GO_ROUTE_SMOKE_CITY_ID is required when route smoke is enabled")
    body: dict[str, Any] = {
        "build_mode": "auto",
        "start_source": "city_center",
        "city_id": config.route_city_id,
        "visit_city_id": config.route_city_id,
        "time_budget_minutes": 180,
        "interests": ["architecture", "history", "nature"],
    }
    if config.route_lat is not None and config.route_lng is not None:
        body.update({"lat": config.route_lat, "lng": config.route_lng})
    else:
        body.update({"lat": 43.238949, "lng": 76.889709})
    return SmokeCheck(name="route_quick", method="POST", path=ROUTE_SMOKE_PATH, body=body)


def build_summary(results: Sequence[SmokeResult], *, run_url: str = "", commit: str = "") -> str:
    ok = all(result.ok for result in results)
    lines = [
        f"{'✅' if ok else '❌'} CITY GO · PRODUCTION SMOKE",
        f"Commit: {commit[:7] if commit else 'unknown'}",
    ]
    for result in results:
        icon = "✅" if result.ok else "❌" if result.status == "failed" else "⚠️"
        detail = f" · {result.detail}" if result.detail else ""
        lines.append(f"{icon} {result.name}: {result.status}{detail}")
    failed = [result for result in results if not result.ok]
    if failed:
        lines.append("Failed checks:")
        lines.extend(f"- {result.name}: {result.detail or result.status}" for result in failed)
    if run_url:
        lines.append(run_url)
    return "\n".join(lines).strip() + "\n"


def write_json_report(results: Sequence[SmokeResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"name": r.name, "status": r.status, "detail": r.detail, "http_status": r.http_status} for r in results]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def config_from_env(args: argparse.Namespace) -> ProductionSmokeConfig:
    return ProductionSmokeConfig(
        base_url=normalize_base_url(args.base_url or os.getenv("PRODUCTION_BASE_URL", "")),
        expected_sha=args.expected_sha or os.getenv("EXPECTED_SHA", ""),
        admin_token=args.admin_token or os.getenv("ADMIN_API_TOKEN", ""),
        route_smoke_enabled=args.route_smoke or os.getenv("CITY_GO_ROUTE_SMOKE_ENABLED", "").lower() == "true",
        route_city_id=args.route_city_id or os.getenv("CITY_GO_ROUTE_SMOKE_CITY_ID", ""),
        route_lat=_optional_float(args.route_lat or os.getenv("CITY_GO_ROUTE_SMOKE_LAT", "")),
        route_lng=_optional_float(args.route_lng or os.getenv("CITY_GO_ROUTE_SMOKE_LNG", "")),
    )


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--expected-sha")
    parser.add_argument("--admin-token")
    parser.add_argument("--route-smoke", action="store_true")
    parser.add_argument("--route-city-id")
    parser.add_argument("--route-lat")
    parser.add_argument("--route-lng")
    parser.add_argument("--summary-file", type=Path, default=Path("/tmp/production-smoke-summary.txt"))
    parser.add_argument("--json-report", type=Path, default=Path("/tmp/production-smoke-report.json"))
    args = parser.parse_args()

    config = config_from_env(args)
    results = run_smoke(config)
    summary = build_summary(
        results,
        run_url=os.getenv("GITHUB_RUN_URL", ""),
        commit=config.expected_sha or os.getenv("GITHUB_SHA", ""),
    )
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    args.summary_file.write_text(summary, encoding="utf-8")
    write_json_report(results, args.json_report)
    print(summary, end="")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
