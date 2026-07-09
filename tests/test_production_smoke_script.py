from __future__ import annotations

import argparse

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
    assert failed_status.detail == "status_failed"


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
