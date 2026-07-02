from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


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
        "manual_build": MANUAL_BUILDER,
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
    normalized_slots = tuple(_normalize_slot(slot) for slot in request.slots)
    min_points = sum(int(slot["min_count"]) for slot in normalized_slots)
    max_points = sum(int(slot["max_count"]) for slot in normalized_slots)
    if min_points < 1:
        raise RouteBuilderV2Error("Slot Builder requires at least one required point")
    if max_points > MAX_ROUTE_POINTS:
        raise RouteBuilderV2Error("Slot Builder exceeds max route points")
    return RouteBuilderV2Plan(
        mode=SLOT_BUILDER,
        executor_mode="instant",
        profile=request.profile,
        route_policy=request.route_policy,
        duration_minutes=request.duration_minutes,
        slots=normalized_slots,
        expected_min_points=min_points,
        expected_max_points=max_points,
    )


def _normalize_slot(slot: Mapping[str, object]) -> dict[str, object]:
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
    return {
        "type": slot_type,
        "min_count": min_count,
        "max_count": max_count,
        "required": bool(slot.get("required", min_count > 0)),
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
