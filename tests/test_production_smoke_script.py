from __future__ import annotations

import pytest

from scripts.production_smoke import (
    ProductionSmokeConfig,
    SmokeCheck,
    SmokeResult,
    build_default_checks,
    build_summary,
    build_url,
    normalize_base_url,
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


@title("Production smoke builds URL without double slashes")
def test_production_smoke_builds_url_without_double_slashes() -> None:
    assert build_url("https://city.example/", "/ready") == "https://city.example/ready"
    assert build_url("https://city.example", "admin/quality") == "https://city.example/admin/quality"


@title("Production smoke includes admin checks only when token exists")
def test_production_smoke_includes_admin_checks_only_when_token_exists() -> None:
    public_only = build_default_checks(ProductionSmokeConfig(base_url="https://city.example"))
    with_admin = build_default_checks(ProductionSmokeConfig(base_url="https://city.example", admin_token="secret"))

    assert [check.name for check in public_only] == ["build", "backend_ready", "frontend"]
    assert "admin_quality" in {check.name for check in with_admin}
    assert all(check.admin for check in with_admin if check.name.startswith("admin_"))


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
    assert route_check.path == "/v1/user-routes/build"
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
        commit="abcdef123456",
        run_url="https://github.example/run/1",
    )

    assert summary.startswith("❌ CITY GO · PRODUCTION SMOKE")
    assert "Commit: abcdef1" in summary
    assert "admin_quality: failed · http_500" in summary
    assert "Failed checks:" in summary
    assert "response" not in summary.lower()
    assert "https://github.example/run/1" in summary


@title("Production smoke check model keeps admin flag explicit")
def test_production_smoke_check_model_keeps_admin_flag_explicit() -> None:
    check = SmokeCheck(name="admin_quality", method="GET", path="/admin/quality", admin=True)

    assert check.admin is True
    assert check.expected_statuses == (200,)
