"""Discovery provider selection."""

from __future__ import annotations

from services.destination_discovery.config import discovery_provider_name
from services.destination_discovery.providers import deterministic, nominatim


def search_regions(query: str, *, limit: int = 5):
    return _module().search_regions(query, limit=limit)


def get_region(region_id: str):
    return _module().get_region(region_id)


def raw_candidates_for_region(region_id: str) -> list[dict[str, object]]:
    return _module().raw_candidates_for_region(region_id)


def _module():
    name = discovery_provider_name()
    if name == "deterministic":
        return deterministic
    if name == "nominatim":
        return nominatim
    return nominatim if name == "auto" else deterministic
