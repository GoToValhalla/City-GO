"""Canonical place/city publication eligibility.

Eligibility evaluates source/product safety, not the current publication read
model. In particular ``Place.is_active`` is written by the publication state
writer, so using it as an input gate would make an ordinary unpublish/republish
cycle impossible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from models.city import City
from models.place import Place
from services.place_public_visibility import is_public_hidden_category
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

NON_PUBLIC_CITY_PUBLICATION_CATEGORIES = HARD_EXCLUDED_CATEGORIES
NON_PUBLIC_CITY_PUBLICATION_LAYERS = {"service", "transport", "utility"}
PLACE_STATUS_ACTIVE = "active"
READY_QUALITY_STATUS = "ready"
SNAPSHOT_MAX_AGE = timedelta(days=30)


@dataclass(frozen=True)
class PlaceEligibility:
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CityPublicationGate:
    allowed: bool
    reasons: tuple[str, ...]


def place_publication_eligibility(place: Place) -> PlaceEligibility:
    """Return source/product blockers for a prospective published state."""

    reasons: list[str] = []
    if place.status not in {None, PLACE_STATUS_ACTIVE}:
        reasons.append("place_status_not_active")
    if str(place.lifecycle_status or "active").strip().lower() in {"closed", "removed", "inactive"}:
        reasons.append("place_lifecycle_not_active")
    category = str(place.canonical_category or place.category or "").strip().lower()
    layer = str(place.place_layer or "").strip().lower()
    if category in NON_PUBLIC_CITY_PUBLICATION_CATEGORIES or layer in NON_PUBLIC_CITY_PUBLICATION_LAYERS:
        reasons.append("non_public_category_or_layer")
    if is_public_hidden_category(place.category):
        reasons.append("public_hidden_category")
    if bool(getattr(place, "is_spam_poi", False)):
        reasons.append("spam_poi")
    if bool(getattr(place, "is_duplicate_suspected", False)):
        reasons.append("duplicate_suspected")
    if place.lat is None or place.lng is None:
        reasons.append("missing_coordinates")
    if not str(place.title or "").strip():
        reasons.append("blank_title")
    return PlaceEligibility(eligible=not reasons, reasons=tuple(reasons))


def city_publication_gate(city: City, *, now: datetime | None = None) -> CityPublicationGate:
    """Require a fresh ready snapshot before any city-wide publish action."""

    now = now or datetime.utcnow()
    reasons: list[str] = []

    from sqlalchemy.orm import object_session
    from services.city_readiness.score import latest_city_readiness_snapshot

    snapshot = None
    session = object_session(city)
    if session is not None:
        snapshot = latest_city_readiness_snapshot(session, city_slug=city.slug)

    if snapshot is None:
        reasons.append("missing_readiness_snapshot")
    else:
        age = now - snapshot.created_at
        if age > SNAPSHOT_MAX_AGE:
            reasons.append("stale_readiness_snapshot")
        if snapshot.quality_status != READY_QUALITY_STATUS:
            reasons.append(f"quality_status_not_ready:{snapshot.quality_status}")

    return CityPublicationGate(allowed=not reasons, reasons=tuple(reasons))
