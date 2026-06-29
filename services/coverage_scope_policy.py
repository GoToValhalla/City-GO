from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CITY_WALKING_SCOPE_TYPES = {"city_core", "city_district", "tourist_core", "food_area", "nature_nearby"}
REGIONAL_SCOPE_TYPES = {"day_trip", "heritage_day_trip", "nature_area", "corridor", "must_have_anchor", "region_pack", "satellite_town"}
INFRA_SCOPE_TYPES = {"service_infra", "transport_hub"}

DEFAULT_SCOPE_TYPE_BY_CODE = {
    "tourist_core": "city_core",
    "food_area": "food_area",
    "food_wider_center": "food_area",
    "useful_services": "service_infra",
}


@dataclass(frozen=True)
class CoverageScopePolicy:
    scope_type: str
    route_policy: str
    transport_required: bool
    max_raw_objects: int | None = None
    max_accepted_places: int | None = None
    human_label: str | None = None


def resolve_scope_policy(scope: object) -> CoverageScopePolicy:
    targets = _coverage_targets(scope)
    code = str(getattr(scope, "code", "") or "")
    import_profile = str(getattr(scope, "import_profile", "") or targets.get("profile") or "")
    scope_type = str(targets.get("scope_type") or targets.get("type") or DEFAULT_SCOPE_TYPE_BY_CODE.get(code) or _type_from_profile(import_profile))
    transport_required = bool(targets.get("transport_required") or targets.get("requires_transport"))
    if scope_type in REGIONAL_SCOPE_TYPES:
        transport_required = True
    route_policy = str(targets.get("route_policy") or _route_policy(scope_type, import_profile))
    return CoverageScopePolicy(
        scope_type=scope_type,
        route_policy=route_policy,
        transport_required=transport_required,
        max_raw_objects=_int_or_none(targets.get("max_raw_objects")),
        max_accepted_places=_int_or_none(targets.get("max_accepted_places")),
        human_label=str(targets.get("human_label") or getattr(scope, "name", "") or code or "") or None,
    )


def scope_is_city_walking(scope: object) -> bool:
    policy = resolve_scope_policy(scope)
    return policy.scope_type in CITY_WALKING_SCOPE_TYPES and not policy.transport_required


def scope_requires_transport(scope: object) -> bool:
    return resolve_scope_policy(scope).transport_required


def _coverage_targets(scope: object) -> dict[str, Any]:
    value = getattr(scope, "coverage_targets", None) or {}
    return value if isinstance(value, dict) else {}


def _type_from_profile(profile: str) -> str:
    if profile in {"service_infra", "useful_services"}:
        return "service_infra"
    if profile == "transport_hub":
        return "transport_hub"
    if profile == "nature_region":
        return "nature_area"
    if profile == "heritage_religious":
        return "heritage_day_trip"
    if profile in {"food_quality", "food_and_coffee"}:
        return "food_area"
    return "city_core"


def _route_policy(scope_type: str, profile: str) -> str:
    if scope_type in INFRA_SCOPE_TYPES:
        return "infra_only" if scope_type == "service_infra" else "transfer_only"
    if scope_type in REGIONAL_SCOPE_TYPES:
        return "day_trip" if scope_type != "region_pack" else "region_scope"
    if profile in {"food_quality", "food_and_coffee"}:
        return "food_stop"
    return "city_walking"


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
