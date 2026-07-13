"""Canonical place/city publication eligibility — the single source of truth
for whether a place or city may become publicly visible.

Before this module existed, three separate publication paths each computed
their own (different, and in two cases missing) eligibility rules:
- admin_city_publication_service.publish_city (place-level only, no city
  readiness/snapshot check at all);
- admin_service.publish_place, gated by publication_policy's
  unsafe_manual_publish_gates (does not check is_spam_poi or
  is_duplicate_suspected);
- admin_place_bulk_service.preview_bulk/apply_bulk (no eligibility check at
  all — preview only described the requested change, apply called
  publish_place, which itself doesn't check spam).

This let a is_spam_poi=true place be published through the bulk path while
city-level publish_city correctly rejected it, and let a needs_review /
readiness_score=46 city become fully published because no city-level gate
existed anywhere. Both are documented, forbidden states under this
project's Publication Safety invariant (local-context/ARCHITECTURE_INVARIANTS.md):
"Auto-publish because an import, enrichment, queue, or UI request
succeeded" is explicitly forbidden.
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
    """The one place-level eligibility check every publication path must use."""
    reasons: list[str] = []
    if not place.is_active:
        reasons.append("place_inactive")
    if place.status not in {None, PLACE_STATUS_ACTIVE}:
        reasons.append("place_status_not_active")
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
    """Canonical city-level readiness gate, required before any city-wide
    publish action. A failed/partial/stalled/running import job or a
    missing/stale snapshot must block publication — see Publication Safety
    and Snapshot Freshness invariants."""
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
