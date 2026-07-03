from __future__ import annotations

import json
from argparse import Namespace

from scripts.production_smoke import (
    ProductionSmokeConfig,
    build_default_checks,
    config_from_env,
    validate_route_response,
)


def test_production_smoke_uses_frontend_api_proxy_for_backend_checks_new() -> None:
    config = ProductionSmokeConfig(base_url="https://example.test")

    paths = {check.name: check.path for check in build_default_checks(config)}

    assert paths["build"] == "/build.json"
    assert paths["frontend"] == "/"
    assert paths["backend_ready"] == "/api/ready"
    assert paths["admin_quality"] == "/api/admin/quality"


def test_production_smoke_adds_route_check_when_enabled_new() -> None:
    config = ProductionSmokeConfig(
        base_url="https://example.test",
        route_smoke_enabled=True,
        route_city_id="yerevan",
        route_lat=40.1792,
        route_lng=44.4991,
    )

    checks = build_default_checks(config)

    route_check = next(check for check in checks if check.name == "route_quick")
    assert route_check.method == "POST"
    assert route_check.path == "/api/v1/user-routes/build"
    assert route_check.body is not None
    assert route_check.body["city_id"] == "yerevan"
    assert route_check.body["time_budget_minutes"] == 120


def test_production_smoke_config_reads_route_env_new(monkeypatch) -> None:
    monkeypatch.setenv("PRODUCTION_BASE_URL", "https://example.test")
    monkeypatch.setenv("CITY_GO_ROUTE_SMOKE_ENABLED", "true")
    monkeypatch.setenv("CITY_GO_ROUTE_SMOKE_CITY_ID", "yerevan")
    monkeypatch.setenv("CITY_GO_ROUTE_SMOKE_LAT", "40.1792")
    monkeypatch.setenv("CITY_GO_ROUTE_SMOKE_LNG", "44.4991")

    config = config_from_env(Namespace(base_url=None, expected_sha=None, admin_token=None, route_smoke=False, route_city_id=None, route_lat=None, route_lng=None))

    assert config.route_smoke_enabled is True
    assert config.route_city_id == "yerevan"
    assert config.route_lat == 40.1792
    assert config.route_lng == 44.4991


def test_production_smoke_fails_route_blocked_category_new() -> None:
    payload = {
        "status": "success",
        "total_places": 2,
        "points": [
            {"title": "Museum", "category": "museum"},
            {"title": "Blocked Stop", "category": "bank"},
        ],
    }

    result = validate_route_response(json.dumps(payload), 200)

    assert result.failed
    assert result.detail == "route_contains_forbidden_junk"


def test_production_smoke_fails_placeholder_route_title_new() -> None:
    payload = {
        "status": "success",
        "total_places": 2,
        "points": [
            {"title": "Museum", "category": "museum"},
            {"title": "Место для прогулки OSM 123", "category": "park"},
        ],
    }

    result = validate_route_response(json.dumps(payload), 200)

    assert result.failed
    assert result.detail == "route_contains_forbidden_junk"


def test_production_smoke_fails_large_budget_overflow_without_weak_reason_new() -> None:
    payload = {
        "status": "success",
        "quality_status": "good",
        "total_places": 3,
        "total_estimated_minutes": 284,
        "time_budget_minutes": 120,
        "points": [
            {"title": "Museum", "category": "museum"},
            {"title": "Park", "category": "park"},
            {"title": "Viewpoint", "category": "viewpoint"},
        ],
    }

    result = validate_route_response(json.dumps(payload), 200)

    assert result.failed
    assert result.detail == "route_budget_overflow"


def test_production_smoke_accepts_honest_weak_short_route_new() -> None:
    payload = {
        "status": "partial_route",
        "quality_status": "weak",
        "total_places": 1,
        "total_estimated_minutes": 80,
        "time_budget_minutes": 120,
        "user_warnings": [{"user_message": "Мало подходящих мест рядом со стартом."}],
        "points": [{"title": "Museum", "category": "museum"}],
    }

    result = validate_route_response(json.dumps(payload), 200)

    assert result.ok
    assert "honest" in result.detail
