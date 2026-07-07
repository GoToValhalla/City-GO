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
    "partial_reason",
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
    base_url = getattr(args, "base_url", None) or os.getenv("PRODUCTION_BASE_URL", "")
    expected_sha = getattr(args, "expected_sha", None) or os.getenv("EXPECTED_SHA", "")
    admin_token = getattr(args, "admin_token", None) or os.getenv("ADMIN_API_TOKEN", "")
    route_smoke_enabled = bool(getattr(args, "route_smoke", False)) or _truthy(os.getenv("CITY_GO_ROUTE_SMOKE_ENABLED", "false"))
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
        if not config.route_city_id:
            raise ValueError("route_city_id is required when route smoke is enabled")
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
        return SmokeResult(check.name, "failed", _http_error_detail(exc), exc.code)
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
    if check.name == "admin_quality":
        return validate_admin_quality_response(raw, http_status)
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


def validate_admin_quality_response(raw: str, http_status: int) -> SmokeResult:
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        return SmokeResult("admin_quality", "failed", "invalid_json", http_status)
    if not isinstance(payload, dict):
        return SmokeResult("admin_quality", "failed", "json_not_object", http_status)
    required_keys = {"items", "total", "todo", "limit", "offset"}
    if not required_keys <= set(payload):
        missing = sorted(required_keys - set(payload))
        return SmokeResult("admin_quality", "failed", f"missing_keys_{missing}", http_status)
    if not isinstance(payload["items"], list):
        return SmokeResult("admin_quality", "failed", "items_not_list", http_status)
    if not isinstance(payload["todo"], list):
        return SmokeResult("admin_quality", "failed", "todo_not_list", http_status)
    if not isinstance(payload["total"], int):
        return SmokeResult("admin_quality", "failed", "total_not_int", http_status)
    if not isinstance(payload["limit"], int):
        return SmokeResult("admin_quality", "failed", "limit_not_int", http_status)
    if not isinstance(payload["offset"], int):
        return SmokeResult("admin_quality", "failed", "offset_not_int", http_status)
    if len(payload["items"]) > payload["limit"]:
        return SmokeResult("admin_quality", "failed", "items_exceeds_limit", http_status)
    return SmokeResult("admin_quality", "ok", f"items_{len(payload['items'])}", http_status)


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
    raw_code_path = _public_payload_raw_technical_code_path(payload)
    if raw_code_path:
        return SmokeResult("route_quick", "failed", f"raw_technical_code_at_{raw_code_path}", http_status)
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


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    base = f"http_{exc.code}"
    try:
        raw = exc.read(4_000).decode("utf-8", errors="replace")
    except Exception:
        return base
    if not raw:
        return base
    try:
        payload = json.loads(raw)
    except ValueError:
        return base
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, list):
        missing = [str(item.get("loc", [""])[-1]) for item in detail if isinstance(item, dict) and item.get("type") == "missing"]
        if missing:
            return f"{base}_missing_{'_'.join(missing[:3])}"
    if isinstance(detail, dict):
        code = detail.get("code") or detail.get("partial_reason")
        if code:
            return f"{base}_{code}"
    if isinstance(detail, str) and detail:
        return f"{base}_{detail[:80]}"
    return base


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
    return False


def _has_large_budget_overflow(payload: Mapping[str, Any]) -> bool:
    requested = _route_requested_budget(payload)
    actual = _route_actual_duration(payload)
    if requested is None or actual is None or requested <= 0:
        return False
    return actual > requested * MAX_NORMAL_ROUTE_BUDGET_OVERFLOW_RATIO


def _route_requested_budget(payload: Mapping[str, Any]) -> float | None:
    for key in ("requested_budget_minutes", "budget_minutes", "time_budget_minutes"):
        value = _number_or_none(payload.get(key))
        if value is not None:
            return value
    request_meta = payload.get("request")
    if isinstance(request_meta, Mapping):
        return _number_or_none(request_meta.get("budget_minutes"))
    return None


def _route_actual_duration(payload: Mapping[str, Any]) -> float | None:
    for key in ("total_duration_minutes", "total_estimated_minutes", "duration_minutes", "estimated_duration_minutes"):
        value = _number_or_none(payload.get(key))
        if value is not None:
            return value
    route = payload.get("route")
    if isinstance(route, Mapping):
        return _number_or_none(route.get("duration_minutes"))
    return None


def _has_honest_weak_reason(status: str, quality_status: str, partial_reason: str, payload: Mapping[str, Any]) -> bool:
    if status in {"partial_route", "partial"} or quality_status == "weak" or partial_reason:
        return True
    for field_name in USER_FACING_ROUTE_FIELDS:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip() and not RAW_TECHNICAL_CODE.match(value.strip()):
            return True
        if isinstance(value, list) and any(isinstance(item, str) and item.strip() and not RAW_TECHNICAL_CODE.match(item.strip()) for item in value):
            return True
    return False


def _public_payload_raw_technical_code_path(payload: Mapping[str, Any]) -> str | None:
    for field_name in USER_FACING_ROUTE_FIELDS:
        if field_name not in payload:
            continue
        nested = _raw_technical_code_path(payload[field_name], field_name)
        if nested:
            return nested
    return None


def _raw_technical_code_path(value: Any, path: str) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return path if text and RAW_TECHNICAL_CODE.match(text) else None
    if isinstance(value, list):
        for index, child in enumerate(value):
            nested = _raw_technical_code_path(child, f"{path}[{index}]")
            if nested:
                return nested
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            nested = _raw_technical_code_path(child, key_path)
            if nested:
                return nested
    return None


def _contains_raw_technical_code(value: Any) -> bool:
    return _raw_technical_code_path(value, "value") is not None


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _route_smoke_check(config: ProductionSmokeConfig) -> SmokeCheck:
    lat = config.route_lat if config.route_lat is not None else DEFAULT_ROUTE_SMOKE_LAT
    lng = config.route_lng if config.route_lng is not None else DEFAULT_ROUTE_SMOKE_LNG
    return SmokeCheck(
        name="route_quick",
        method="POST",
        path=ROUTE_SMOKE_PATH,
        body={
            "build_mode": "auto",
            "city_id": config.route_city_id or DEFAULT_ROUTE_SMOKE_CITY_ID,
            "lat": lat,
            "lng": lng,
            "start_source": "map_point",
            "start": {
                "type": "map_point",
                "lat": lat,
                "lng": lng,
            },
            "mode": "quick",
            "time_budget_minutes": ROUTE_SMOKE_BUDGET_MINUTES,
            "interests": ["architecture", "history"],
        },
    )


def build_summary(results: Sequence[SmokeResult], run_url: str = "", commit: str = "") -> str:
    """Backward-compatible summary builder used by smoke tests."""
    if any(result.failed for result in results):
        status = "❌"
    elif any(result.skipped for result in results):
        status = "⚠️"
    else:
        status = "✅"

    lines = [f"{status} CITY GO · PRODUCTION SMOKE"]
    if commit:
        lines.append(f"Commit: {commit[:7]}")
    for result in results:
        icon = "✅" if result.ok else "❌"
        if result.skipped:
            icon = "⚠️"
        detail = f" · {result.detail}" if result.detail else ""
        lines.append(f"{icon} {result.name}: {result.status}{detail}")

    failures = [result for result in results if result.failed]
    skipped = [result for result in results if result.skipped]

    if failures:
        lines.append("")
        lines.append("Failed checks:")
        for result in failures:
            lines.append(f"- {result.name}: {result.detail or result.status}")
    if skipped:
        lines.append("")
        lines.append("Skipped checks:")
        for result in skipped:
            lines.append(f"- {result.name}: {result.detail or result.status}")

    if run_url:
        lines.append("")
        lines.append(f"GitHub Actions: {run_url}")

    return "\n".join(lines)


def summarize_results(results: Sequence[SmokeResult], expected_sha: str = "") -> str:
    status = "✅" if all(result.ok for result in results) else "❌"
    lines = [f"{status} CITY GO · PRODUCTION SMOKE"]
    if expected_sha:
        lines.append(f"Commit: {expected_sha[:7]}")
    for result in results:
        icon = "✅" if result.ok else "❌"
        if result.skipped:
            icon = "⚠️"
        detail = f" · {result.detail}" if result.detail else ""
        lines.append(f"{icon} {result.name}: {result.status}{detail}")
    failures = [result for result in results if result.failed]
    if failures:
        lines.append("")
        lines.append("Failed checks:")
        for result in failures:
            lines.append(f"- {result.name}: {result.detail or result.status}")
    run_url = os.getenv("GITHUB_RUN_URL", "").strip()
    if run_url:
        lines.append("")
        lines.append(f"GitHub Actions: {run_url}")
    return "\n".join(lines)


def write_reports(results: Sequence[SmokeResult], summary_file: str | None, json_report: str | None, expected_sha: str = "") -> None:
    if summary_file:
        Path(summary_file).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_file).write_text(summarize_results(results, expected_sha=expected_sha), encoding="utf-8")
    if json_report:
        Path(json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(json_report).write_text(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run City GO production smoke checks")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--admin-token", default="")
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--json-report", default="")
    parser.add_argument("--route-smoke", action="store_true")
    parser.add_argument("--route-city-id", default="")
    parser.add_argument("--route-lat", type=float, default=None)
    parser.add_argument("--route-lng", type=float, default=None)
    return parser.parse_args()


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    args = parse_args()
    config = config_from_env(args)
    results = run_smoke(config)
    print(summarize_results(results, expected_sha=config.expected_sha))
    write_reports(results, args.summary_file, args.json_report, expected_sha=config.expected_sha)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
