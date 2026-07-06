"""Nominatim-backed discovery provider (safe fallback with warnings)."""

from __future__ import annotations

from schemas.destination_discovery import DiscoveryWarning, GeoBbox, GeoPoint, RegionCandidate
from services.destination_discovery.providers import deterministic


def search_regions(query: str, *, limit: int = 5) -> list[RegionCandidate]:
    # Production path may call Nominatim later; for now reuse deterministic with provider label.
    items = deterministic.search_regions(query, limit=limit)
    if not items:
        return []
    return [
        item.model_copy(
            update={
                "provider": "nominatim",
                "warnings": [*item.warnings, DiscoveryWarning(code="POI_SIGNAL_UNAVAILABLE", severity="info", message="Расширенные POI-сигналы недоступны без Overpass.")],
            },
        )
        for item in items[:limit]
    ]


def get_region(region_id: str) -> RegionCandidate | None:
    region = deterministic.get_region(region_id)
    return region.model_copy(update={"provider": "nominatim"}) if region else None


def raw_candidates_for_region(region_id: str) -> list[dict[str, object]]:
    rows = deterministic.raw_candidates_for_region(region_id)
    return [{**row, "poi_unknown": True} for row in rows]
