from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


class RouteBuilderV2Error(ValueError):
    pass


QUICK_BUILD = "quick"
CATEGORY_BUILDER = "category"
MANUAL_BUILDER = "manual"
SLOT_BUILDER = "slot"

ROUTE_BUILDER_V2_MODES: tuple[str, ...] = (
    QUICK_BUILD,
    CATEGORY_BUILDER,
    MANUAL_BUILDER,
    SLOT_BUILDER,
)

BUILD_MODE_TO_ROUTE_BUILDER_MODE: Mapping[str, str] = {
    "auto": QUICK_BUILD,
    "by_categories": CATEGORY_BUILDER,
    "manual": MANUAL_BUILDER,
    "constructor": SLOT_BUILDER,
}

ROUTE_BUILDER_V2_BLOCKED_CATEGORIES = frozenset(
    {
        "apteka",
        "atm",
        "bank",
        "bench",
        "bus_stop",
        "fuel",
        "mall",
        "parking",
        "pharmacy",
        "service",
        "shop",
        "supermarket",
        "toilet",
        "transport",
        "utility",
    }
)
ROUTE_BUILDER_V2_BLOCKED_TITLE_TOKENS = (
    "аптек",
    "pharmacy",
    "остановк",
    "bus stop",
    "банкомат",
    "atm",
)

DEFAULT_ROUTE_POLICY = "city_walking"
DEFAULT_PROFILE = "overview"
MIN_MANUAL_POINTS = 2
MAX_ROUTE_POINTS = 12


@dataclass(frozen=True)
class RouteBuilderV2Request:
    mode: str
    city_id: int | None = None
    city_slug: str | None = None
    profile: str = DEFAULT_PROFILE
    route_policy: str = DEFAULT_ROUTE_POLICY
    duration_minutes: int | None = None
    categories: tuple[str, ...] = ()
    selected_place_ids: tuple[int, ...] = ()
    slots: tuple[Mapping[str, object], ...] = ()
    interests: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteBuilderV2Plan:
    mode: str
    executor_mode: str
    profile: str
    route_policy: str
    duration_minutes: int | None
    categories: tuple[str, ...] = ()
    selected_place_ids: tuple[int, ...] = ()
    slots: tuple[Mapping[str, object], ...] = ()
    expected_min_points: int = 0
    expected_max_points: int = MAX_ROUTE_POINTS
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RouteBuilderV2GateResult:
    points: tuple[object, ...]
    removed_junk_place_ids: tuple[str, ...]
    warnings: tuple[str, ...]


def build_route_builder_v2_plan(request: RouteBuilderV2Request | Mapping[str, object]) -> RouteBuilderV2Plan:
    normalized = normalize_route_builder_request(request)
    if normalized.mode == QUICK_BUILD:
        return _build_quick_plan(normalized)
    if normalized.mode == CATEGORY_BUILDER:
        return _build_category_plan(normalized)
    if normalized.mode == MANUAL_BUILDER:
        return _build_manual_plan(normalized)
    if normalized.mode == SLOT_BUILDER:
        return _build_slot_plan(normalized)
    raise RouteBuilderV2Error(f"Unsupported route builder mode: {normalized.mode}")


def build_route_builder_v2_plan_from_intent(intent: object) -> RouteBuilderV2Plan:
    """Build the Route Builder v2 execution plan from the public user route API payload."""

    return build_route_builder_v2_plan(route_builder_v2_payload_from_intent(intent))


def route_builder_v2_payload_from_intent(intent: object) -> dict[str, object]:
    build_mode = str(getattr(intent, "build_mode", "auto") or "auto")
    mode = BUILD_MODE_TO_ROUTE_BUILDER_MODE.get(build_mode, build_mode)
    city_value = getattr(intent, "city_id", None) or getattr(intent, "visit_city_id", None)
    selected_ids = getattr(intent, "selected_place_ids", []) or []
    slots = getattr(intent, "route_slots", []) or []
    interests = list(getattr(intent, "interests", []) or [])
    return {
        "mode": mode,
        "city_slug": str(city_value) if city_value else None,
        "duration_minutes": getattr(intent, "time_budget_minutes", None),
        "categories": interests if mode == CATEGORY_BUILDER else [],
        "selected_place_ids": selected_ids,
        "slots": slots,
        "interests": interests,
    }


def apply_route_builder_v2_plan_to_intent(intent: object, plan: RouteBuilderV2Plan) -> object:
    """Translate v2 modes into the existing route engine input without bypassing production route code."""

    updates: dict[str, object] = {}
    if plan.duration_minutes is not None:
        updates["time_budget_minutes"] = plan.duration_minutes
    if plan.mode == CATEGORY_BUILDER:
        updates["interests"] = _merge_unique_strings(getattr(intent, "interests", []) or [], plan.categories)
    if plan.mode == SLOT_BUILDER:
        slot_interests = [str(slot.get("type") or slot.get("category") or "") for slot in plan.slots]
        updates["interests"] = _merge_unique_strings(getattr(intent, "interests", []) or [], slot_interests)
    if not updates:
        return intent
    if hasattr(intent, "model_copy"):
        return intent.model_copy(update=updates)
    raise RouteBuilderV2Error("Route Builder v2 expected a pydantic route intent")


def attach_route_builder_v2_result(state: object, plan: RouteBuilderV2Plan) -> object:
    """Attach v2 metadata and enforce post-build output gates on the public route state."""

    gate = route_builder_v2_output_gate(getattr(state, "points", []) or [])
    warnings = _unique_strings(
        [
            *list(getattr(state, "warnings", []) or []),
            *plan.warnings,
            *gate.warnings,
        ]
    )
    status = str(getattr(state, "status", "ready") or "ready")
    partial_reason = getattr(state, "partial_reason", None)
    if len(gate.points) < plan.expected_min_points and status not in {"failed", "no_route"}:
        status = "partial_route" if gate.points else "no_route"
        partial_reason = "route_builder_v2_insufficient_points"
        warnings = _unique_strings([*warnings, "route_builder_v2_insufficient_points"])

    explanation = dict(getattr(state, "explanation", {}) or {})
    explanation["route_builder_v2"] = {
        "mode": plan.mode,
        "executor_mode": plan.executor_mode,
        "expected_min_points": plan.expected_min_points,
        "expected_max_points": plan.expected_max_points,
        "removed_junk_place_ids": list(gate.removed_junk_place_ids),
    }
    debug_trace = [
        {
            "stage": "route_builder_v2",
            "mode": plan.mode,
            "executor_mode": plan.executor_mode,
            "status": "ok" if not gate.removed_junk_place_ids else "sanitized",
            "expected_min_points": plan.expected_min_points,
            "expected_max_points": plan.expected_max_points,
            "output_count": len(gate.points),
            "removed_junk_place_ids": list(gate.removed_junk_place_ids),
            "data_contract": "public_catalog_visible_route_eligible_only",
        },
        *list(getattr(state, "debug_trace", []) or []),
    ]
    category_distribution = _category_distribution(gate.points)
    updates = {
        "status": status,
        "partial_reason": partial_reason,
        "points": list(gate.points),
        "total_places": len(gate.points),
        "category_distribution": category_distribution,
        "warnings": warnings,
        "has_warnings": bool(warnings),
        "warning_count": len(warnings),
        "explanation": explanation,
        "debug_trace": debug_trace,
    }
    if hasattr(state, "model_copy"):
        return state.model_copy(update=updates)
    raise RouteBuilderV2Error("Route Builder v2 expected a pydantic route state")


def route_builder_v2_output_gate(points: Sequence[object]) -> RouteBuilderV2GateResult:
    kept: list[object] = []
    removed: list[str] = []
    for point in points:
        if _is_route_junk(point):
            removed.append(str(getattr(point, "place_id", "")))
        else:
            kept.append(point)
    warnings = ("route_builder_v2_removed_route_junk",) if removed else ()
    return RouteBuilderV2GateResult(points=tuple(kept), removed_junk_place_ids=tuple(removed), warnings=warnings)


def normalize_route_builder_request(request: RouteBuilderV2Request | Mapping[str, object]) -> RouteBuilderV2Request:
    if isinstance(request, RouteBuilderV2Request):
        raw = {
            "mode": request.mode,
            "city_id": request.city_id,
            "city_slug": request.city_slug,
            "profile": request.profile,
            "route_policy": request.route_policy,
            "duration_minutes": request.duration_minutes,
            "categories": request.categories,
            "selected_place_ids": request.selected_place_ids,
            "slots": request.slots,
            "interests": request.interests,
        }
    else:
        raw = dict(request)

    mode = normalize_mode(raw.get("mode"))
    city_id = _optional_int(raw.get("city_id"))
    city_slug = _optional_text(raw.get("city_slug"))
    if city_id is None and not city_slug:
        raise RouteBuilderV2Error("Route Builder v2 requires city_id or city_slug")

    duration = _optional_int(raw.get("duration_minutes"))
    if duration is not None and duration <= 0:
        raise RouteBuilderV2Error("duration_minutes must be positive")

    return RouteBuilderV2Request(
        mode=mode,
        city_id=city_id,
        city_slug=city_slug,
        profile=_optional_text(raw.get("profile")) or DEFAULT_PROFILE,
        route_policy=_optional_text(raw.get("route_policy")) or DEFAULT_ROUTE_POLICY,
        duration_minutes=duration,
        categories=_normalize_text_list(raw.get("categories")),
        selected_place_ids=_normalize_id_list(raw.get("selected_place_ids")),
        slots=tuple(dict(slot) for slot in raw.get("slots") or ()),
        interests=_normalize_text_list(raw.get("interests")),
    )


def normalize_mode(mode: object) -> str:
    normalized = str(mode or "").strip().lower().replace("_builder", "")
    aliases = {
        "auto": QUICK_BUILD,
        "instant": QUICK_BUILD,
        "quick_build": QUICK_BUILD,
        "categories": CATEGORY_BUILDER,
        "category_build": CATEGORY_BUILDER,
        "by_categories": CATEGORY_BUILDER,
        "manual_build": MANUAL_BUILDER,
        "constructor": SLOT_BUILDER,
        "slots": SLOT_BUILDER,
        "slot_build": SLOT_BUILDER,
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in ROUTE_BUILDER_V2_MODES:
        raise RouteBuilderV2Error(f"Unsupported route builder mode: {mode}")
    return normalized


def assert_route_builder_v2_mode_supported(mode: str) -> None:
    normalize_mode(mode)


def _build_quick_plan(request: RouteBuilderV2Request) -> RouteBuilderV2Plan:
    warnings: list[str] = []
    if request.categories:
        warnings.append("quick_ignores_categories")
    if request.selected_place_ids:
        warnings.append("quick_ignores_manual_selection")
    return RouteBuilderV2Plan(
        mode=QUICK_BUILD,
        executor_mode="instant",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        expected_min_points=3,
        warnings=tuple(warnings),
    )


def _build_category_plan(request: RouteBuilderV2Request) -> RouteBuilderV2Plan:
    if not request.categories:
        raise RouteBuilderV2Error("Category Builder requires at least one category")
    return RouteBuilderV2Plan(
        mode=CATEGORY_BUILDER,
        executor_mode="instant",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        categories=request.categories,
        expected_min_points=max(2, min(len(request.categories), MAX_ROUTE_POINTS)),
    )


def _build_manual_plan(request: RouteBuilderV2Request) -> RouteBuilderV2Plan:
    if len(request.selected_place_ids) < MIN_MANUAL_POINTS:
        raise RouteBuilderV2Error("Manual Builder requires at least two selected places")
    return RouteBuilderV2Plan(
        mode=MANUAL_BUILDER,
        executor_mode="instant",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        selected_place_ids=request.selected_place_ids,
        expected_min_points=len(request.selected_place_ids),
        expected_max_points=len(request.selected_place_ids),
    )


def _build_slot_plan(request: RouteBuilderV2Request) -> RouteBuilderV2Plan:
    if not request.slots:
        raise RouteBuilderV2Error("Slot Builder requires at least one slot")
    normalized_slots = tuple(_normalize_slot(index, slot) for index, slot in enumerate(request.slots, 1))
    min_points = sum(int(slot["min_count"]) for slot in normalized_slots)
    max_points = sum(int(slot["max_count"]) for slot in normalized_slots)
    if min_points < 1:
        raise RouteBuilderV2Error("Slot Builder requires at least one required point")
    if max_points > MAX_ROUTE_POINTS:
        raise RouteBuilderV2Error("Slot Builder exceeds max route points")
    return RouteBuilderV2Plan(
        mode=SLOT_BUILDER,
        executor_mode="slot_constructor",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        slots=normalized_slots,
        expected_min_points=min_points,
        expected_max_points=max_points,
    )


def _normalize_slot(index: int, slot: Mapping[str, object]) -> dict[str, object]:
    slot_type = _optional_text(slot.get("type")) or _optional_text(slot.get("category"))
    if not slot_type:
        raise RouteBuilderV2Error("Slot requires type or category")
    min_count = _optional_int(slot.get("min_count"))
    max_count = _optional_int(slot.get("max_count"))
    if min_count is None:
        min_count = 1
    if max_count is None:
        max_count = min_count
    if min_count < 0 or max_count < 1 or min_count > max_count:
        raise RouteBuilderV2Error("Invalid slot count bounds")
    selected_place_id = _optional_text(slot.get("selected_place_id"))
    return {
        "slot_id": _optional_text(slot.get("slot_id")) or f"slot-{index}",
        "type": slot_type,
        "category": slot_type,
        "min_count": min_count,
        "max_count": max_count,
        "required": bool(slot.get("required", min_count > 0)),
        "duration": _optional_int(slot.get("duration")),
        "selected_place_id": selected_place_id,
    }


def _normalize_text_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values = [value]
    else:
        raw_values = list(value)  # type: ignore[arg-type]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = _optional_text(item)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return tuple(result)


def _normalize_id_list(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    result: list[int] = []
    seen: set[int] = set()
    for item in list(value):  # type: ignore[arg-type]
        item_id = _optional_int(item)
        if item_id is not None and item_id > 0 and item_id not in seen:
            result.append(item_id)
            seen.add(item_id)
    return tuple(result)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RouteBuilderV2Error(f"Expected integer value: {value}") from exc


def _merge_unique_strings(left: Sequence[object], right: Sequence[object]) -> list[str]:
    return _unique_strings([str(item).strip().lower() for item in [*left, *right] if str(item).strip()])


def _unique_strings(values: Sequence[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _is_route_junk(point: object) -> bool:
    category = str(getattr(point, "category", "") or "").strip().lower()
    title = str(getattr(point, "title", "") or "").strip().lower()
    if category in ROUTE_BUILDER_V2_BLOCKED_CATEGORIES:
        return True
    return any(token in title for token in ROUTE_BUILDER_V2_BLOCKED_TITLE_TOKENS)


def _category_distribution(points: Sequence[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for point in points:
        category = str(getattr(point, "category", "") or "unknown")
        result[category] = result.get(category, 0) + 1
    return result
