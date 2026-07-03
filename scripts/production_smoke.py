#!/usr/bin/env python3
"""Production smoke checks for City GO post-deploy verification.

The public production base URL points at the frontend container. Backend API checks
must therefore go through the same `/api` nginx proxy that the browser uses.
The script intentionally prints a compact, safe summary and never includes response
bodies from authenticated admin endpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_PUBLIC_CHECKS: tuple[tuple[str, str], ...] = (
    ("build", "/build.json"),
    ("frontend", "/"),
)

DEFAULT_BACKEND_CHECKS: tuple[tuple[str, str], ...] = (
    ("backend_ready", "/api/ready"),
)

DEFAULT_ADMIN_CHECKS: tuple[tuple[str, str], ...] = (
    ("admin_system_health", "/api/admin/system-health"),
    ("admin_quality", "/api/admin/quality"),
    ("admin_taxonomy_categories", "/api/admin/taxonomy/categories?limit=1"),
)

ROUTE_SMOKE_PATH = "/api/v1/user-routes/build"
DEFAULT_ROUTE_SMOKE_CITY_ID = "yerevan"
DEFAULT_ROUTE_SMOKE_LAT = 40.1792
DEFAULT_ROUTE_SMOKE_LNG = 44.4991
ROUTE_SMOKE_BUDGET_MINUTES = 120
RAW_TECHNICAL_CODE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+){1,}$")
TRACEBACK_MARKERS = ("Traceback (most recent call last)", "sqlalchemy.exc", "pydantic_core", "Internal Server Error")
PLACEHOLDER_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*культурн(?:ое|ый|ая)\s+(?:место|объект)\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*место\s+для\s+прогулки\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*place\s+for\s+walk\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*парк\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*пляж\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*[a-zа-я ]+\s+osm\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*osm\s+(node|way|relation)?\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*(node|way|relation)\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*unnamed\s+(poi|place|point)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(unnamed|unknown|без\s+названия|место\s+без\s+названия)\s*$", re.IGNORECASE),
)
HARD_EXCLUDED_CATEGORIES = frozenset(
    {
        "medical", "health", "healthcare", "hospital", "clinic", "pharmacy", "apteka",
        "bank", "atm", "parking", "fuel", "toilet", "toilets", "public_toilet",
        "police", "bus_stop", "stop", "transport", "public_transport", "service",
        "services", "utility", "industrial", "shelter", "post_office",
        "vending_machine", "bench", "waste_basket", "charging_station",
        "car_service", "mvd", "government", "military", "cemetery", "waste_disposal",
        "generic_service", "transport_stop", "tram_stop", "gas_station", "useful",
        "unknown", "other", "office", "hotel", "shopping", "shop", "supermarket",
        "shopping_mall", "mall",
    }
)
FORBIDDEN_ROUTE_JUNK = HARD_EXCLUDED_CATEGORIES | frozenset(
    {
        "pharmacy",
        "apteka",
        "bus_stop",
        "stop",
        "bank",
        "atm",
        "parking",
        "fuel",
        "toilet",
        "toilets",
        "utility",
        "service",
        "services",
        "transport",
        "health",
        "healthcare",
        "clinic",
        "hospital",
    }
)
MAX_NORMAL_ROUTE_BUDGET_OVERFLOW_RATIO = 2.0
USER_FACING_ROUTE_FIELDS = (
    "warnings",
    "user_warnings",
    "user_explanation",
    "explanation",
)


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
        return self.status in {"ok", "skipped"}

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    @property
    def skipped(self) -> bool:
        return self.status == "skipped"


@dataclass(frozen=True)
class ProductionSmokeConfig:
    base_url: str
    expected_sha: str = ""
    admin_token: str = ""
    route_smoke_enabled: bool = False
    route_city_id: str = ""
    route_lat: float | None = None
    route_lng: float | None = None


def is_placeholder_title(title: str | None) -> bool:
    text = str(title or "").strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in PLACEHOLDER_TITLE_PATTERNS)


def normalize_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    if not url:
        raise ValueError("PRODUCTION_BASE_URL or SSH_HOST is required")
    if not url.startswith(("http://", "https://")):
        raise ValueError("production smoke base URL must start with http:// or https://")
    return url


def resolve_base_url(candidate: str, ssh_host: str = "") -> str:
    if candidate.strip():
        return normalize_base_url(candidate)
    host = ssh_host.strip()
    if host:
        return normalize_base_url(f"http://{host}")
    return normalize_base_url("")


def config_from_env(args: argparse.Namespace) -> ProductionSmokeConfig:
    """Build config from CLI-like args and environment variables.

    Kept as a public helper because regression tests and workflow code import it
    directly. CLI values win over environment values when provided.
    """
    base_url = getattr(args, "base_url", None) or os.getenv("PRODUCTION_BASE_URL", "")
    expected_sha = getattr(args, "expected_sha", None) or os.getenv("EXPECTED_SHA", "")
    admin_token = getattr(args, "admin_token", None) or os.getenv("ADMIN_API_TOKEN", "")
    route_smoke_arg = getattr(args, "route_smoke", None)
    route_smoke_enabled = bool(route_smoke_arg) if route_smoke_arg is not None else _truthy(os.getenv("CITY_GO_ROUTE_SMOKE_ENABLED", "false"))
    route_city_id = getattr(args, "route_city_id", None) or os.getenv("CITY_GO_ROUTE_SMOKE_CITY_ID", DEFAULT_ROUTE_SMOKE_CITY_ID)
    route_lat_raw = getattr(args, "route_lat", None)
    route_lng_raw = getattr(args, "route_lng", None)
    route_lat = _float_or_none(str(route_lat_raw if route_lat_raw is not None else os.getenv("CITY_GO_ROUTE_SMOKE_LAT", str(DEFAULT_ROUTE_SMOKE_LAT))))
    route_lng = _float_or_none(str(route_lng_raw if route_lng_raw is not None else os.getenv("CITY_GO_ROUTE_SMOKE_LNG", str(DEFAULT_ROUTE_SMOKE_LNG))))
    return ProductionSmokeConfig(
        base_url=resolve_base_url(str(base_url or ""), os.getenv("SSH_HOST", "")),
        expected_sha=str(expected_sha or "").strip(),
        admin_token=str(admin_token or "").strip(),
        route_smoke_enabled=route_smoke_enabled,
        route_city_id=str(route_city_id or ""),
        route_lat=route_lat,
        route_lng=route_lng,
    )


def build_default_checks(config: ProductionSmokeConfig) -> list[SmokeCheck]:
    checks = [SmokeCheck(name=name, method="GET", path=path) for name, path in DEFAULT_PUBLIC_CHECKS]
    checks.extend(SmokeCheck(name=name, method="GET", path=path) for name, path in DEFAULT_BACKEND_CHECKS)
    checks.extend(SmokeCheck(name=name, method="GET", path=path, admin=True) for name, path in DEFAULT_ADMIN_CHECKS)
    if config.route_smoke_enabled:
        checks.append(_route_smoke_check(config))
    return checks


def run_smoke(config: ProductionSmokeConfig, checks: Sequence[SmokeCheck] | None = None) -> list[SmokeResult]:
    selected_checks = list(checks or build_default_checks(config))
    results: list[SmokeResult] = []
    for check in selected_checks:
        result = execute_check(config, check)
        if result.status == "ok" and check.name == "build" and config.expected_sha:
            result = validate_build_sha(result, config.expected_sha)
        results.append(result)
    return results


def execute_check(config: ProductionSmokeConfig, check: SmokeCheck) -> SmokeResult:
    headers = {"User-Agent": "city-go-production-smoke/1.0"}
    if check.admin:
        if not config.admin_token:
            return SmokeResult(check.name, "skipped", "ADMIN_API_TOKEN secret is not configured")
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

    if _contains_traceback(raw):
        return SmokeResult(check.name, "failed", "raw_traceback_or_internal_error", http_status)
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

    if not isinstance(payload, dict):
        return SmokeResult("route_quick", "failed", "json_not_object", http_status)

    status = str(payload.get("status") or "")
    points = payload.get("points") if isinstance(payload.get("points"), list) else []
    total_places = int(payload.get("total_places") or len(points))
    quality_status = str(payload.get("quality_status") or payload.get("route_quality_status") or "")
    partial_reason = str(payload.get("partial_reason") or "")
    has_honest_reason = _has_honest_weak_reason(status, quality_status, partial_reason, payload)

    if status in {"failed", "empty", "preview_failed"}:
        return SmokeResult("route_quick", "failed", f"status_{status}", http_status)
    if _contains_forbidden_route_junk(points):
        return SmokeResult("route_quick", "failed", "route_contains_forbidden_junk", http_status)
    if _public_payload_has_raw_technical_codes(payload):
        return SmokeResult("route_quick", "failed", "raw_technical_codes_in_public_payload", http_status)
    if _has_large_budget_overflow(payload) and not has_honest_reason:
        return SmokeResult("route_quick", "failed", "route_budget_overflow", http_status)

    minimum_points = minimum_points_for_budget(ROUTE_SMOKE_BUDGET_MINUTES)
    if total_places < minimum_points and not has_honest_reason:
        return SmokeResult("route_quick", "failed", f"expected_min_{minimum_points}_points_got_{total_places}", http_status)

    reason = f"points_{total_places}"
    if has_honest_reason and (status == "partial_route" or quality_status == "weak" or partial_reason or total_places < minimum_points or _has_large_budget_overflow(payload)):
        reason = f"honest_{status or quality_status or 'limited'}_{reason}"
    return SmokeResult("route_quick", "ok", reason, http_status)


def minimum_points_for_budget(budget_minutes: int) -> int:
    if budget_minutes < 75:
        return 1
    return 2


def _contains_traceback(raw: str) -> bool:
    return any(marker in raw for marker in TRACEBACK_MARKERS)


def _contains_forbidden_route_junk(points: Sequence[Any]) -> bool:
    for point in points:
        if not isinstance(point, dict):
            continue
        category = str(point.get("category") or "").strip().lower()
        title = str(point.get("title") or "").strip()
        if category in FORBIDDEN_ROUTE_JUNK:
            return True
        if is_placeholder_title(title):
            return True
        if any(token in title.lower() for token in ("аптек", "pharmacy", "остановк", "bus stop", "банкомат", "atm", "институт хирургии")):
            return True
    return False


def _public_payload_has_raw_technical_codes(payload: Mapping[str, Any]) -> bool:
    for field in USER_FACING_ROUTE_FIELDS:
        if _contains_raw_code(payload.get(field)):
            return True
    return False


def _contains_raw_code(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(RAW_TECHNICAL_CODE.fullmatch(value.strip()))
    if isinstance(value, Mapping):
        return any(_contains_raw_code(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_raw_code(item) for item in value)
    return False


def _has_honest_weak_reason(status: str, quality_status: str, partial_reason: str, payload: Mapping[str, Any]) -> bool:
    if status == "partial_route" or quality_status == "weak" or partial_reason:
        return True
    warnings = payload.get("user_warnings") or payload.get("warnings") or []
    return bool(warnings)


def _has_large_budget_overflow(payload: Mapping[str, Any]) -> bool:
    total = _int_payload(payload, "total_estimated_minutes", "total_duration_minutes", "estimated_minutes")
    budget = _int_payload(payload, "time_budget_minutes", "requested_budget_minutes", "budget_minutes")
    if not total or not budget:
        context = payload.get("context")
        budget = _int_payload(context, "time_budget_minutes", "requested_budget_minutes") if isinstance(context, Mapping) else budget
    return bool(total and budget and total >= int(budget * MAX_NORMAL_ROUTE_BUDGET_OVERFLOW_RATIO))


def _int_payload(payload: Mapping[str, Any] | None, *keys: str) -> int:
    if not isinstance(payload, Mapping):
        return 0
    for key in keys:
        try:
            value = int(payload.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0


def _route_smoke_check(config: ProductionSmokeConfig) -> SmokeCheck:
    route_city_id = config.route_city_id.strip()
    if not route_city_id:
        raise ValueError("CITY_GO_ROUTE_SMOKE_CITY_ID is required when route smoke is enabled")
    body: dict[str, Any] = {
        "build_mode": "auto",
        "start_source": "city_center",
        "city_id": route_city_id,
        "visit_city_id": route_city_id,
        "time_budget_minutes": ROUTE_SMOKE_BUDGET_MINUTES,
        "interests": ["architecture", "history", "museum", "walk"],
    }
    if config.route_lat is not None and config.route_lng is not None:
        body.update({"lat": config.route_lat, "lng": config.route_lng})
    else:
        body.update({"lat": DEFAULT_ROUTE_SMOKE_LAT, "lng": DEFAULT_ROUTE_SMOKE_LNG})
    return SmokeCheck(name="route_quick", method="POST", path=ROUTE_SMOKE_PATH, body=body)


def build_summary(results: Sequence[SmokeResult], *, run_url: str = "", commit: str = "") -> str:
    failed = [result for result in results if result.failed]
    skipped = [result for result in results if result.skipped]
    header_icon = "❌" if failed else "⚠️" if skipped else "✅"
    lines = [
        f"{header_icon} CITY GO · PRODUCTION SMOKE",
        f"Commit: {commit[:7] if commit else 'unknown'}",
    ]
    for result in results:
        icon = "✅" if result.status == "ok" else "⚠️" if result.skipped else "❌"
        detail = f" · {result.detail}" if result.detail else ""
        lines.append(f"{icon} {result.name}: {result.status}{detail}")
    if failed:
        lines.append("")
        lines.append("Failed checks:")
        lines.extend(f"- {result.name}: {result.detail or result.status}" for result in failed)
    if skipped:
        lines.append("")
        lines.append("Skipped checks:")
        lines.extend(f"- {result.name}: {result.detail or result.status}" for result in skipped)
    if run_url:
        lines.append("")
        lines.append(f"GitHub Actions: {run_url}")
    return "\n".join(lines)


def write_reports(results: Sequence[SmokeResult], summary_file: str, json_report: str, *, run_url: str = "", commit: str = "") -> None:
    summary = build_summary(results, run_url=run_url, commit=commit)
    Path(summary_file).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_file).write_text(summary + "\n", encoding="utf-8")
    Path(json_report).parent.mkdir(parents=True, exist_ok=True)
    Path(json_report).write_text(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run production smoke checks")
    parser.add_argument("--base-url", default=os.getenv("PRODUCTION_BASE_URL", ""))
    parser.add_argument("--ssh-host", default=os.getenv("SSH_HOST", ""))
    parser.add_argument("--expected-sha", default=os.getenv("EXPECTED_SHA", ""))
    parser.add_argument("--admin-token", default=os.getenv("ADMIN_API_TOKEN", ""))
    parser.add_argument("--summary-file", default="/tmp/production-smoke/summary.txt")
    parser.add_argument("--json-report", default="/tmp/production-smoke/report.json")
    parser.add_argument("--run-url", default=os.getenv("GITHUB_RUN_URL", ""))
    parser.add_argument("--commit", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--route-smoke-enabled", default=os.getenv("CITY_GO_ROUTE_SMOKE_ENABLED", "false"))
    parser.add_argument("--route-city-id", default=os.getenv("CITY_GO_ROUTE_SMOKE_CITY_ID", DEFAULT_ROUTE_SMOKE_CITY_ID))
    parser.add_argument("--route-lat", default=os.getenv("CITY_GO_ROUTE_SMOKE_LAT", str(DEFAULT_ROUTE_SMOKE_LAT)))
    parser.add_argument("--route-lng", default=os.getenv("CITY_GO_ROUTE_SMOKE_LNG", str(DEFAULT_ROUTE_SMOKE_LNG)))
    return parser.parse_args()


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_or_none(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    config = ProductionSmokeConfig(
        base_url=resolve_base_url(args.base_url, args.ssh_host),
        expected_sha=args.expected_sha.strip(),
        admin_token=args.admin_token.strip(),
        route_smoke_enabled=_truthy(str(args.route_smoke_enabled)),
        route_city_id=str(args.route_city_id or ""),
        route_lat=_float_or_none(str(args.route_lat)),
        route_lng=_float_or_none(str(args.route_lng)),
    )
    results = run_smoke(config)
    write_reports(results, args.summary_file, args.json_report, run_url=args.run_url, commit=args.commit)
    print(build_summary(results, run_url=args.run_url, commit=args.commit))
    return 1 if any(result.failed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
