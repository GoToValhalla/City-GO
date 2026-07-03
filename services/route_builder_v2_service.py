from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from services.place_quality_signals import is_placeholder_title
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES
from services.route_user_warnings import route_warning_copy, route_warning_message


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

ROUTE_BUILDER_V2_BLOCKED_CATEGORIES = HARD_EXCLUDED_CATEGORIES
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
    raw_warnings = _unique_strings(
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
        raw_warnings = _unique_strings([*raw_warnings, "route_builder_v2_insufficient_points"])

    public_warnings = [route_warning_message(code) for code in raw_warnings]
    explanation = dict(getattr(state, "explanation", {}) or {})
    explanation["warnings"] = public_warnings
    explanation["data_limitations"] = [route_warning_message(note) for note in list(explanation.get("data_limitations", []) or [])]
    explanation["data_notes"] = [route_warning_message(note) for note in list(explanation.get("data_notes", []) or [])]
    explanation["route_builder_v2"] = {
        "mode": _public_mode_label(plan.mode),
        "expected_points": f"от {plan.expected_min_points} до {plan.expected_max_points}",
        "removed_places_count": len(gate.removed_junk_place_ids),
        "message": "Маршрут проверен на неподходящие сервисные точки.",
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
        "warnings": public_warnings,
        "user_warnings": _public_user_warnings(raw_warnings, getattr(state, "places_with_warnings", []) or []),
        "has_warnings": bool(public_warnings),
        "warning_count": len(public_warnings),
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
    city_id = _optional_positive_int(raw.get("city_id"))
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
        profile=_normalized_label(raw.get("profile")) or DEFAULT_PROFILE,
        route_policy=_normalized_label(raw.get("route_policy")) or DEFAULT_ROUTE_POLICY,
        duration_minutes=duration,
        categories=_normalize_text_list(raw.get("categories")),
        selected_place_ids=_normalize_id_list(raw.get("selected_place_ids")),
        slots=_normalize_slots(raw.get("slots")),
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
    if len(request.slots) > MAX_ROUTE_POINTS:
        raise RouteBuilderV2Error(f"Slot Builder supports up to {MAX_ROUTE_POINTS} slots")
    min_points = sum(int(slot.get("min_count", 1) or 1) for slot in request.slots)
    max_points = sum(int(slot.get("max_count", slot.get("min_count", 1)) or 1) for slot in request.slots)
    if max_points > MAX_ROUTE_POINTS:
        raise RouteBuilderV2Error(f"Slot Builder supports up to {MAX_ROUTE_POINTS} points")
    if max_points < min_points:
        raise RouteBuilderV2Error("Slot Builder max_count cannot be lower than min_count")
    return RouteBuilderV2Plan(
        mode=SLOT_BUILDER,
        executor_mode="slot",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        slots=request.slots,
        expected_min_points=min_points,
        expected_max_points=max_points,
    )


def _optional_positive_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_text_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(_unique_strings(str(item).strip().lower() for item in value if str(item).strip()))


def _normalize_id_list(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    ids: list[int] = []
    for item in value:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0 and number not in ids:
            ids.append(number)
    return tuple(ids)


def _normalize_slots(value: object) -> tuple[Mapping[str, object], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    slots: list[Mapping[str, object]] = []
    for slot in value:
        if isinstance(slot, Mapping):
            slots.append(dict(slot))
    return tuple(slots)


def _merge_unique_strings(*values: Sequence[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in value:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
    return result


def _unique_strings(values: Sequence[object]) -> list[str]:
    return _merge_unique_strings(values)


def _is_route_junk(point: object) -> bool:
    category = str(getattr(point, "category", "") or "").strip().lower()
    if category in ROUTE_BUILDER_V2_BLOCKED_CATEGORIES:
        return True
    title = str(getattr(point, "title", "") or "")
    if is_placeholder_title(title):
        return True
    title_lower = title.casefold()
    return any(token in title_lower for token in ROUTE_BUILDER_V2_BLOCKED_TITLE_TOKENS)


def _category_distribution(points: Sequence[object]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for point in points:
        category = str(getattr(point, "category", "unknown") or "unknown")
        distribution[category] = distribution.get(category, 0) + 1
    return distribution


def _public_user_warnings(warnings: Sequence[str], places_with_time_warnings: Sequence[object]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for warning in warnings:
        mapped = route_warning_copy(str(warning))
        if mapped:
            _, severity, message, hint = mapped
            items.append(_warning_item("route", severity, message, (), hint))
        else:
            message = route_warning_message(str(warning))
            if message.strip():
                items.append(_warning_item("route", "warning", message, (), "Проверьте детали маршрута перед стартом."))
    place_ids = tuple(str(item) for item in places_with_time_warnings if str(item))
    if place_ids:
        items.append(_warning_item("budget", "warning", "У части мест есть риск по времени работы.", place_ids, "Откройте карточку места и проверьте часы перед визитом."))
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (str(item.get("type") or ""), str(item.get("severity") or ""), str(item.get("user_message") or ""))
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _warning_item(kind: str, severity: str, message: str, place_ids: Sequence[str], hint: str) -> dict[str, object]:
    return {
        "type": kind if kind in {"route", "data", "budget", "walk", "interest"} else "route",
        "severity": severity,
        "user_message": message,
        "affected_place_ids": list(place_ids),
        "action_hint": hint,
    }


def _public_mode_label(mode: str) -> str:
    labels = {
        QUICK_BUILD: "Быстрый маршрут",
        CATEGORY_BUILDER: "По категориям",
        MANUAL_BUILDER: "Ручной маршрут",
        SLOT_BUILDER: "Конструктор маршрута",
    }
    return labels.get(mode, "Маршрут")
