#!/usr/bin/env python3
"""Fast pre-deploy public route API contract gate.

This gate is intentionally local and data-free: it validates the public payload
shape that production smoke later checks against the real deployed app. It lets
CI catch route warning/explanation contract regressions before a slow deploy.
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from schemas.user_route import UserRouteBuildRequest, UserRoutePoint, UserRouteState
from services.route_builder_v2_service import attach_route_builder_v2_result, build_route_builder_v2_plan_from_intent
from services.route_finalize_types import FinalRoute
from services.user_route_mapper import final_route_to_state

RAW_TECHNICAL_CODE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+){1,}$")
USER_FACING_ROUTE_FIELDS = ("warnings", "user_warnings", "explanation")
PUBLIC_WARNING_TYPES = {"route", "data", "budget", "walk", "interest"}


def main() -> int:
    failures: list[str] = []
    for name, payload in _sample_payloads().items():
        failures.extend(f"{name}: {failure}" for failure in _validate_public_payload(payload))
    if failures:
        print("❌ Route public contract gate failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("✅ Route public contract gate passed")
    return 0


def _sample_payloads() -> dict[str, Mapping[str, Any]]:
    return {
        "mapper_warning_sanitization": _mapper_warning_payload(),
        "route_builder_v2_output_gate": _route_builder_v2_payload(),
    }


def _mapper_warning_payload() -> Mapping[str, Any]:
    intent = UserRouteBuildRequest(lat=40.1792, lng=44.4991, city_id="yerevan", time_budget_minutes=120)
    final = FinalRoute(
        route_id="contract-route",
        status="partial_route",
        points=[],
        total_minutes=0,
        total_places=0,
        estimated_distance=0.0,
        warnings=[
            "route_builder_v2_insufficient_points",
            "unknown_internal_code",
            "Не нашли мест рядом с выбранным стартом.",
        ],
        has_warnings=True,
        warning_count=3,
    )
    return final_route_to_state(final, intent).model_dump(mode="json")


def _route_builder_v2_payload() -> Mapping[str, Any]:
    request = UserRouteBuildRequest(
        lat=43.238949,
        lng=76.889709,
        start_source="city_center",
        build_mode="auto",
        time_budget_minutes=120,
        interests=[],
        city_id="almaty",
    )
    plan = build_route_builder_v2_plan_from_intent(request)
    state = UserRouteState(
        route_id="route-1",
        status="ready",
        context=request,
        total_places=1,
        total_minutes=30,
        total_estimated_minutes=40,
        estimated_distance=1.0,
        has_warnings=False,
        warning_count=0,
        quality_score=0.5,
        quality_status="weak",
        warnings=[],
        points=[_point("1", "park", "Central park")],
        explanation={"warnings": ["route_builder_v2_insufficient_points"]},
        debug_trace=[],
    )
    return attach_route_builder_v2_result(state, plan).model_dump(mode="json")


def _point(place_id: str, category: str, title: str) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=place_id,
        city_slug="almaty",
        position=int(place_id),
        title=title,
        address="Main street 1",
        lat=43.2,
        lng=76.8,
        category=category,
        visit_minutes=20,
    )


def _validate_public_payload(payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in USER_FACING_ROUTE_FIELDS:
        raw_path = _first_raw_code_path(payload.get(field), field)
        if raw_path:
            failures.append(f"raw technical code leaked at {raw_path}")
    for index, warning in enumerate(payload.get("user_warnings") or []):
        if not isinstance(warning, Mapping):
            failures.append(f"user_warnings[{index}] is not an object")
            continue
        warning_type = str(warning.get("type") or "")
        if warning_type not in PUBLIC_WARNING_TYPES:
            failures.append(f"user_warnings[{index}].type is not public: {warning_type}")
        message = str(warning.get("user_message") or "")
        if not message or _is_raw_code(message):
            failures.append(f"user_warnings[{index}].user_message is not user-facing: {message}")
    return failures


def _first_raw_code_path(value: Any, path: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return path if _is_raw_code(value) else ""
    if isinstance(value, Mapping):
        for key, item in value.items():
            nested = _first_raw_code_path(item, f"{path}.{key}")
            if nested:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        for index, item in enumerate(value):
            nested = _first_raw_code_path(item, f"{path}[{index}]")
            if nested:
                return nested
    return ""


def _is_raw_code(value: str) -> bool:
    return bool(RAW_TECHNICAL_CODE.fullmatch(value.strip()))


if __name__ == "__main__":
    raise SystemExit(main())
