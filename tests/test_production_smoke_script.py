from __future__ import annotations

import argparse
import json
import re

import pytest

from scripts.production_smoke import (
    ProductionSmokeConfig,
    SmokeCheck,
    SmokeResult,
    build_default_checks,
    build_summary,
    build_url,
    config_from_env,
    execute_check,
    normalize_base_url,
    resolve_base_url,
    safe_build_detail,
    validate_build_sha,
    validate_route_response,
)
from tests.allure_support import title


@title("Production smoke validates base URL")
def test_production_smoke_validates_base_url() -> None:
    assert normalize_base_url("https://example.com/") == "https://example.com"

    with pytest.raises(ValueError):
        normalize_base_url("")

    with pytest.raises(ValueError):
        normalize_base_url("example.com")


@title("Production smoke never uses SSH_HOST/raw IP as the public HTTPS target")
def test_production_smoke_ignores_ssh_host_and_defaults_to_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    # SSH_HOST is the raw production IP, used for SSH/deploy — the TLS cert is
    # issued for the domain, so it must never become the public smoke target.
    assert resolve_base_url("", "203.0.113.10") == "https://citygo.autismishe.online"
    assert resolve_base_url("https://city.example", "203.0.113.10") == "https://city.example"

    monkeypatch.setenv("SSH_HOST", "203.0.113.10")
    args = argparse.Namespace(
        base_url=None,
        expected_sha=None,
        admin_token=None,
        route_smoke=False,
        route_city_id=None,
        route_lat=None,
        route_lng=None,
    )

    assert config_from_env(args).base_url == "https://citygo.autismishe.online"


@title("Production smoke reports missing target as skipped")
def test_production_smoke_reports_missing_target_as_skipped_summary() -> None:
    summary = build_summary(
        [SmokeResult("production_base_url", "skipped", "PRODUCTION_BASE_URL or SSH_HOST is required")],
        commit="abcdef123456",
    )

    assert summary.startswith("⚠️ CITY GO · PRODUCTION SMOKE")
    assert "production_base_url: skipped" in summary
    assert "Skipped checks:" in summary
    assert "Failed checks:" not in summary


@title("Production smoke builds URL without double slashes")
def test_production_smoke_builds_url_without_double_slashes() -> None:
    assert build_url("https://city.example/", "/ready") == "https://city.example/ready"
    assert build_url("https://city.example", "admin/quality") == "https://city.example/admin/quality"


@title("Production smoke keeps admin checks visible without requiring token")
def test_production_smoke_keeps_admin_checks_visible_without_requiring_token() -> None:
    checks = build_default_checks(ProductionSmokeConfig(base_url="https://city.example"))

    names = [check.name for check in checks]
    assert names[:3] == ["build", "frontend", "backend_ready"]
    assert "admin_quality" in names
    assert all(check.path.startswith("/api/admin/") for check in checks if check.name.startswith("admin_"))
    assert all(check.admin for check in checks if check.name.startswith("admin_"))


@title("Production smoke skips admin checks when token is not configured")
def test_production_smoke_skips_admin_checks_when_token_is_not_configured() -> None:
    result = execute_check(
        ProductionSmokeConfig(base_url="https://city.example"),
        SmokeCheck(name="admin_quality", method="GET", path="/api/admin/quality", admin=True),
    )

    assert result.status == "skipped"
    assert result.ok
    assert result.detail == "ADMIN_API_TOKEN secret is not configured"


@title("Production smoke can include route smoke request")
def test_production_smoke_can_include_route_smoke_request() -> None:
    checks = build_default_checks(
        ProductionSmokeConfig(
            base_url="https://city.example",
            route_smoke_enabled=True,
            route_city_id="1",
        )
    )

    route_check = next(check for check in checks if check.name == "route_quick")
    assert route_check.method == "POST"
    assert route_check.path == "/api/v1/user-routes/build"
    assert route_check.body is not None
    assert route_check.body["build_mode"] == "auto"
    assert route_check.body["city_id"] == "1"

    with pytest.raises(ValueError):
        build_default_checks(ProductionSmokeConfig(base_url="https://city.example", route_smoke_enabled=True))


@title("Production smoke validates build sha from build json")
def test_production_smoke_validates_build_sha_from_build_json() -> None:
    assert safe_build_detail('{"sha":"abcdef123456"}') == "sha_abcdef1"
    assert safe_build_detail("not json") == "invalid_json"

    ok = validate_build_sha(SmokeResult("build", "ok", "sha_abcdef1", 200), "abcdef123456")
    failed = validate_build_sha(SmokeResult("build", "ok", "sha_fffffff", 200), "abcdef123456")

    assert ok.ok
    assert not failed.ok
    assert failed.detail == "expected_abcdef1_got_fffffff"


@title("Production smoke validates route response")
def test_production_smoke_validates_route_response() -> None:
    ok = validate_route_response('{"status":"ready","total_places":3}', 200)
    failed_empty = validate_route_response('{"status":"ready","total_places":1}', 200)
    failed_status = validate_route_response('{"status":"failed","total_places":5}', 200)

    assert ok.ok
    assert ok.detail == "points_3"
    assert not failed_empty.ok
    assert failed_empty.detail == "expected_min_2_points_got_1"
    assert not failed_status.ok
    assert failed_status.detail == "status_failed__points_5"


# --- route_quick failed/empty/preview_failed safe diagnostic detail ---


@title("route_quick failed status includes sanitized partial_reason")
def test_route_quick_failed_detail_includes_partial_reason() -> None:
    result = validate_route_response(
        '{"status":"failed","total_places":0,"partial_reason":"Not Enough Places!!"}', 200
    )

    assert not result.ok
    assert result.detail == "status_failed__reason_not_enough_places__points_0"


@title("route_quick failed status includes sanitized quality_status")
def test_route_quick_failed_detail_includes_quality_status() -> None:
    result = validate_route_response(
        '{"status":"empty","total_places":0,"quality_status":"WEAK"}', 200
    )

    assert not result.ok
    assert result.detail == "status_empty__quality_weak__points_0"

    fallback = validate_route_response(
        '{"status":"empty","total_places":0,"route_quality_status":"low"}', 200
    )
    assert fallback.detail == "status_empty__quality_low__points_0"


@title("route_quick failed status includes final debug_trace stage and error")
def test_route_quick_failed_detail_includes_debug_trace_stage_and_error() -> None:
    result = validate_route_response(
        json.dumps(
            {
                "status": "preview_failed",
                "total_places": 0,
                "debug_trace": [
                    {"stage": "candidate_scoring", "status": "ok"},
                    {"stage": "route_assembly", "error_code": "NO_CANDIDATES_LEFT"},
                ],
            }
        ),
        200,
    )

    assert not result.ok
    assert result.detail == "status_preview_failed__points_0__stage_route_assembly__error_no_candidates_left"


@title("route_quick failed detail omits missing optional fields instead of fabricating them")
def test_route_quick_failed_detail_omits_missing_fields() -> None:
    result = validate_route_response('{"status":"failed"}', 200)

    assert not result.ok
    assert result.detail == "status_failed__points_0"
    assert "reason_" not in result.detail
    assert "quality_" not in result.detail
    assert "stage_" not in result.detail
    assert "error_" not in result.detail


@title("route_quick failed detail sanitizes and truncates malicious/long free text")
def test_route_quick_failed_detail_sanitizes_malicious_input() -> None:
    malicious_reason = "'; DROP TABLE places; -- <script>alert(1)</script> " + ("x" * 200)
    result = validate_route_response(
        json.dumps({"status": "failed", "total_places": 0, "partial_reason": malicious_reason}),
        200,
    )

    assert not result.ok
    assert "DROP" not in result.detail
    assert "<script>" not in result.detail
    assert ";" not in result.detail
    assert "'" not in result.detail
    assert " " not in result.detail
    # every token, including the sanitized reason, is capped
    for token in result.detail.split("__"):
        assert len(token) <= len("reason_") + 40
    assert re.fullmatch(r"[a-z0-9_]+", result.detail)


@title("route_quick failed detail never includes coordinates, addresses, or place titles")
def test_route_quick_failed_detail_never_includes_sensitive_fields() -> None:
    result = validate_route_response(
        json.dumps(
            {
                "status": "failed",
                "total_places": 1,
                "points": [
                    {
                        "title": "Кафе Секретное",
                        "address": "ул. Тайная, 42",
                        "lat": 40.123456,
                        "lng": 44.654321,
                        "category": "cafe",
                    }
                ],
                "user": {"token": "super-secret-token", "id": 42},
                "request": {"lat": 40.123456, "lng": 44.654321},
            }
        ),
        200,
    )

    assert not result.ok
    assert "секретное" not in result.detail.lower()
    assert "тайная" not in result.detail.lower()
    assert "40" not in result.detail
    assert "44" not in result.detail
    assert "token" not in result.detail
    assert "super-secret" not in result.detail


@title("route_quick failed detail never includes the full response body or a stack trace")
def test_route_quick_failed_detail_never_includes_raw_body_or_traceback() -> None:
    raw = json.dumps(
        {
            "status": "failed",
            "total_places": 0,
            "partial_reason": "no_candidates",
            "debug_trace": [
                {
                    "stage": "route_assembly",
                    "error": "boom",
                    "traceback": "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: boom",
                }
            ],
        }
    )
    result = validate_route_response(raw, 200)

    assert not result.ok
    assert "Traceback" not in result.detail
    assert "File \"" not in result.detail
    assert "line 1" not in result.detail
    assert len(result.detail) < len(raw)


@title("route_quick successful and partial-route detail behavior is unchanged")
def test_route_quick_success_and_partial_detail_unchanged() -> None:
    ok = validate_route_response('{"status":"ready","total_places":3}', 200)
    assert ok.ok
    assert ok.detail == "points_3"

    partial = validate_route_response(
        json.dumps({"status": "partial_route", "total_places": 2, "partial_reason": "Мест не хватило для полного бюджета"}), 200
    )
    assert partial.ok
    assert partial.detail == "honest_partial_route_points_2"


@title("Production smoke summary lists failed checks without response bodies")
def test_production_smoke_summary_lists_failed_checks_without_response_bodies() -> None:
    summary = build_summary(
        [
            SmokeResult("build", "ok", "sha_abcdef1", 200),
            SmokeResult("admin_quality", "failed", "http_500", 500),
            SmokeResult("admin_taxonomy_categories", "ok", "http_200", 200),
        ],
        run_url="https://github.example/run/1",
        commit="abcdef123456",
    )

    assert summary.startswith("❌ CITY GO · PRODUCTION SMOKE")
    assert "admin_quality: failed · http_500" in summary
    assert "Failed checks:" in summary
    assert "response" not in summary.lower()
    assert "https://github.example/run/1" in summary
