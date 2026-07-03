from __future__ import annotations

import json

import pytest

from scripts.production_smoke import (
    ROUTE_SMOKE_PATH,
    USER_FACING_ROUTE_FIELDS,
    ProductionSmokeConfig,
    SmokeResult,
    build_default_checks,
    build_url,
    minimum_points_for_budget,
    validate_build_sha,
    validate_route_response,
)
from scripts.route_public_contract_gate import USER_FACING_ROUTE_FIELDS as GATE_USER_FACING_ROUTE_FIELDS

RAW_CODE = "_".join(("route", "builder", "v2", "insufficient", "points"))


def _payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "success",
        "quality_status": "good",
        "total_places": 2,
        "total_estimated_minutes": 90,
        "time_budget_minutes": 120,
        "warnings": ["Маршрут собран."],
        "user_warnings": [{"type": "route", "user_message": "Маршрут собран."}],
        "explanation": {"warnings": ["Маршрут собран."]},
        "points": [
            {"title": "Museum", "category": "museum"},
            {"title": "Central park", "category": "park"},
        ],
    }
    payload.update(updates)
    return payload


def _result(payload: dict[str, object]):
    return validate_route_response(json.dumps(payload, ensure_ascii=False), 200)


def test_production_smoke_and_predeploy_gate_use_same_user_facing_fields_new() -> None:
    assert USER_FACING_ROUTE_FIELDS == GATE_USER_FACING_ROUTE_FIELDS


def test_production_smoke_route_check_uses_frontend_nginx_api_proxy_new() -> None:
    config = ProductionSmokeConfig(base_url="https://city.example", route_smoke_enabled=True, route_city_id="yerevan")
    route_check = next(check for check in build_default_checks(config) if check.name == "route_quick")

    assert route_check.path == ROUTE_SMOKE_PATH == "/api/v1/user-routes/build"
    assert build_url(config.base_url, route_check.path) == "https://city.example/api/v1/user-routes/build"


@pytest.mark.parametrize("field", USER_FACING_ROUTE_FIELDS)
def test_production_smoke_rejects_raw_code_in_every_user_facing_route_field_new(field: str) -> None:
    payload = _payload()
    if field == "warnings":
        payload[field] = [RAW_CODE]
    elif field == "user_warnings":
        payload[field] = [{"type": "route", "user_message": RAW_CODE}]
    elif field == "user_explanation":
        payload[field] = {"message": RAW_CODE}
    elif field == "explanation":
        payload[field] = {"warnings": [RAW_CODE]}

    result = _result(payload)

    assert result.failed
    assert result.detail == "raw_technical_codes_in_public_payload"


@pytest.mark.parametrize("title", ["OSM node 123", "Node 123", "Way 123", "Unnamed POI"])
def test_production_smoke_rejects_placeholder_titles_new(title: str) -> None:
    payload = _payload(points=[{"title": "Museum", "category": "museum"}, {"title": title, "category": "park"}])

    result = _result(payload)

    assert result.failed
    assert result.detail == "route_contains_forbidden_junk"


@pytest.mark.parametrize(
    "bad_payload,detail",
    [
        ("not-json", "invalid_json"),
        ([], "json_not_object"),
        ({"status": "failed", "points": []}, "status_failed"),
        ({"status": "empty", "points": []}, "status_empty"),
        ({"status": "preview_failed", "points": []}, "status_preview_failed"),
    ],
)
def test_production_smoke_rejects_invalid_route_payload_shapes_new(bad_payload: object, detail: str) -> None:
    raw = bad_payload if isinstance(bad_payload, str) else json.dumps(bad_payload)

    result = validate_route_response(raw, 200)

    assert result.failed
    assert result.detail == detail


def test_production_smoke_rejects_successful_route_that_is_too_short_without_honest_reason_new() -> None:
    payload = _payload(total_places=1, points=[{"title": "Museum", "category": "museum"}], warnings=[], user_warnings=[])

    result = _result(payload)

    assert result.failed
    assert result.detail == "expected_min_2_points_got_1"


@pytest.mark.parametrize(
    "status,quality_status,partial_reason,warnings",
    [
        ("partial_route", "good", "", []),
        ("success", "weak", "", []),
        ("success", "good", "route_short_due_to_low_place_density", []),
        ("success", "good", "", ["Подходящих точек пока мало."]),
    ],
)
def test_production_smoke_accepts_short_route_only_with_honest_reason_new(
    status: str,
    quality_status: str,
    partial_reason: str,
    warnings: list[str],
) -> None:
    payload = _payload(
        status=status,
        quality_status=quality_status,
        partial_reason=partial_reason,
        total_places=1,
        points=[{"title": "Museum", "category": "museum"}],
        warnings=warnings,
    )

    result = _result(payload)

    assert result.ok
    assert "honest" in result.detail


def test_production_smoke_rejects_large_budget_overflow_without_honest_reason_new() -> None:
    payload = _payload(total_places=3, total_estimated_minutes=300, time_budget_minutes=120, warnings=[], user_warnings=[])

    result = _result(payload)

    assert result.failed
    assert result.detail == "route_budget_overflow"


def test_production_smoke_accepts_large_budget_overflow_with_weak_quality_reason_new() -> None:
    payload = _payload(total_places=3, total_estimated_minutes=300, time_budget_minutes=120, quality_status="weak")

    result = _result(payload)

    assert result.ok
    assert result.detail.startswith("honest_")


@pytest.mark.parametrize("budget,expected", [(15, 1), (74, 1), (75, 2), (120, 2)])
def test_production_smoke_minimum_points_for_budget_new(budget: int, expected: int) -> None:
    assert minimum_points_for_budget(budget) == expected


def test_production_smoke_validates_build_sha_match_new() -> None:
    result = validate_build_sha(SmokeResult("build", "ok", "sha_abcdef1", 200), "abcdef123456")

    assert result.ok


def test_production_smoke_validates_build_sha_mismatch_new() -> None:
    result = validate_build_sha(SmokeResult("build", "ok", "sha_abcdef1", 200), "1234567890")

    assert result.failed
    assert result.detail == "expected_1234567_got_abcdef1"
