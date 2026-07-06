from __future__ import annotations

import os
from dataclasses import dataclass

from data.scripts import import_city_osm as legacy_osm
from data.scripts.import_city_osm_v2 import COVERAGE_AWARE_PROFILE_FILTERS
from models.destination import Destination, DestinationScope
from services.destination_bbox import point_in_bbox
from services.osm_import_taxonomy import category_from_osm_tags


@dataclass(frozen=True)
class DestinationCandidate:
    slug: str
    title: str
    category: str
    lat: float
    lng: float
    source: str
    changes: dict[str, object]


class DestinationSourceError(RuntimeError):
    pass


def collect_scope_candidates(destination: Destination, scope: DestinationScope) -> list[DestinationCandidate]:
    if _adapter_name() == "deterministic":
        return collect_deterministic_scope_candidates(destination, scope)
    return collect_osm_scope_candidates(destination, scope)


def collect_osm_scope_candidates(destination: Destination, scope: DestinationScope) -> list[DestinationCandidate]:
    bbox = _bbox(scope.bbox or destination.bbox)
    if bbox is None:
        return []
    try:
        _install_osm_contract()
        raw = legacy_osm._fetch_osm_objects(bbox, scope.import_profile)
        normalized = [legacy_osm._normalize_osm_object(item, destination.slug) for item in raw]
    except (Exception, SystemExit) as exc:
        raise DestinationSourceError(str(exc) or exc.__class__.__name__) from exc
    accepted = [item for item in normalized if item.get("accepted")]
    return [_candidate_from_osm(item) for item in accepted if point_in_bbox(item["raw_lat"], item["raw_lng"], bbox)]


def collect_deterministic_scope_candidates(destination: Destination, scope: DestinationScope) -> list[DestinationCandidate]:
    center = _center(scope.bbox or destination.bbox, destination.center_lat, destination.center_lng)
    if center is None:
        return []
    lat, lng = center
    candidates = [
        _candidate(destination, scope, "viewpoint", "Смотровая точка", "viewpoint", lat, lng),
        _candidate(destination, scope, "cafe", "Кафе у маршрута", "cafe", lat + 0.001, lng + 0.001),
        _candidate(destination, scope, "bus-stop", "Остановка транспорта", "bus_stop", lat - 0.001, lng - 0.001),
        _candidate(destination, scope, "outside", "Вне контура", "museum", lat + 9.0, lng + 9.0),
    ]
    return [item for item in candidates if point_in_bbox(item.lat, item.lng, scope.bbox or destination.bbox)]


def _adapter_name() -> str:
    return os.getenv("CITYGO_DESTINATION_SOURCE_ADAPTER", "osm_overpass").strip().lower()


def _install_osm_contract() -> None:
    legacy_osm.PROFILE_FILTERS = COVERAGE_AWARE_PROFILE_FILTERS
    legacy_osm._category = category_from_osm_tags


def _candidate_from_osm(item: dict[str, object]) -> DestinationCandidate:
    category = str(item["category"])
    changes = {
        "short_description": item.get("short_description"),
        "address": item.get("address"),
        "opening_hours": item.get("opening_hours"),
        "average_visit_duration_minutes": 25,
        "category": category,
        "canonical_category": category,
    }
    return DestinationCandidate(
        slug=str(item["slug"]),
        title=str(item["title"]),
        category=category,
        lat=float(item["raw_lat"]),
        lng=float(item["raw_lng"]),
        source="osm_overpass",
        changes={key: value for key, value in changes.items() if value is not None},
    )


def _candidate(destination: Destination, scope: DestinationScope, suffix: str, label: str, category: str, lat: float, lng: float) -> DestinationCandidate:
    slug = f"{destination.slug}-{scope.code}-{suffix}".lower().replace("_", "-")
    return DestinationCandidate(
        slug=slug,
        title=f"{label}: {scope.name}",
        category=category,
        lat=lat,
        lng=lng,
        source="destination_scope_deterministic",
        changes=_changes(category, scope.name),
    )


def _changes(category: str, scope_name: str) -> dict[str, object]:
    return {
        "short_description": f"Проверенное место в контуре «{scope_name}».",
        "address": f"{scope_name}, ориентир в пределах направления",
        "opening_hours": {"text": "Ежедневно"},
        "average_visit_duration_minutes": 25,
        "category": category,
        "canonical_category": category,
    }


def _center(bbox: dict[str, object] | None, lat: float | None, lng: float | None) -> tuple[float, float] | None:
    if bbox:
        try:
            south, north = float(bbox.get("south") or bbox.get("min_lat")), float(bbox.get("north") or bbox.get("max_lat"))
            west, east = float(bbox.get("west") or bbox.get("min_lng")), float(bbox.get("east") or bbox.get("max_lng"))
            return ((south + north) / 2, (west + east) / 2)
        except (TypeError, ValueError):
            return None
    return (float(lat), float(lng)) if lat is not None and lng is not None else None


def _bbox(value: dict[str, object] | None) -> dict[str, float] | None:
    if not value:
        return None
    try:
        return {
            "south": float(value.get("south") or value.get("min_lat")),
            "west": float(value.get("west") or value.get("min_lng")),
            "north": float(value.get("north") or value.get("max_lat")),
            "east": float(value.get("east") or value.get("max_lng")),
        }
    except (AttributeError, TypeError, ValueError):
        return None
