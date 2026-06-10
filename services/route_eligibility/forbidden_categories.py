"""Категории, запрещённые для маршрутов (не удаляются из БД)."""

from __future__ import annotations

from services.import_quality_categories import NON_TOURIST_CATEGORIES
from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES

# Канон + OSM-алиасы + служебные POI из product spec.
_EXPLICIT_FORBIDDEN: frozenset[str] = frozenset({
    "pharmacy", "hospital", "clinic", "bus_stop", "tram_stop",
    "gas_station", "toilet", "police", "industrial", "office",
    "generic_service", "transport_stop", "stop", "shelter",
})

ROUTE_FORBIDDEN_CATEGORIES: frozenset[str] = (
    PUBLIC_HIDDEN_CATEGORIES | NON_TOURIST_CATEGORIES | _EXPLICIT_FORBIDDEN
)

ALGORITHM_VERSION = "route_eligibility_v1"
