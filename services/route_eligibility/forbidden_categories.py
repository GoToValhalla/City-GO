"""Категории, запрещённые для маршрутов (не удаляются из БД)."""

from __future__ import annotations

from services.data_foundation_policy import SPAM_POI_CATEGORIES
from services.import_quality_categories import NON_TOURIST_CATEGORIES
from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES

# Канон + OSM-алиасы + служебные POI из Data Foundation spec.
ROUTE_FORBIDDEN_CATEGORIES: frozenset[str] = (
    PUBLIC_HIDDEN_CATEGORIES | NON_TOURIST_CATEGORIES | SPAM_POI_CATEGORIES
)

ALGORITHM_VERSION = "route_eligibility_v2_data_foundation"
