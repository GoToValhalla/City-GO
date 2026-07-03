"""Deprecated route-forbidden category constant wrapper."""

from __future__ import annotations

from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

ROUTE_FORBIDDEN_CATEGORIES: frozenset[str] = HARD_EXCLUDED_CATEGORIES

ALGORITHM_VERSION = "route_eligibility_v2_data_foundation"
