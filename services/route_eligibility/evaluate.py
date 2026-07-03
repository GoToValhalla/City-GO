"""Deprecated wrapper for the CITYGO-171 route eligibility policy."""

from __future__ import annotations

from services.route_eligibility_policy import RouteEligibilityVerdict as RouteEligibilityResult
from services.route_eligibility_policy import evaluate_place_route_eligibility
