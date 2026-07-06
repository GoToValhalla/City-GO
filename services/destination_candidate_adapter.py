from __future__ import annotations

from dataclasses import dataclass

from models.destination import Destination, DestinationScope
from services.destination_bbox import point_in_bbox


@dataclass(frozen=True)
class DestinationCandidate:
    slug: str
    title: str
    category: str
    lat: float
    lng: float
    source: str
    changes: dict[str, object]


def collect_scope_candidates(destination: Destination, scope: DestinationScope) -> list[DestinationCandidate]:
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
