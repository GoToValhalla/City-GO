from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.source_observation import SourceObservation
from services.osm_import_taxonomy import classify_osm_place


def apply_place_layers(db: Session, *, city_slug: str | None = None, scope_id: int | None = None) -> dict[str, object]:
    query = (
        db.query(SourceObservation, Place, CityImportScope)
        .join(Place, Place.id == SourceObservation.canonical_place_id)
        .outerjoin(CityImportScope, CityImportScope.id == SourceObservation.scope_id)
        .join(City, City.id == Place.city_id)
        .filter(SourceObservation.source_type == "osm", SourceObservation.canonical_place_id.isnot(None))
    )
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if scope_id:
        query = query.filter(SourceObservation.scope_id == scope_id)

    counters: Counter[str] = Counter()
    updated = 0
    for observation, place, scope in query.order_by(SourceObservation.id.asc()).all():
        targets = (scope.coverage_targets or {}) if scope is not None else {}
        scope_type = str(targets.get("scope_type") or targets.get("type") or (scope.code if scope else ""))
        transport_required = bool(targets.get("transport_required") or targets.get("requires_transport"))
        profile = str((scope.import_profile if scope else None) or targets.get("profile") or "")
        classification = classify_osm_place(
            _tags(observation.raw_payload),
            profile=profile,
            scope_type=scope_type,
            transport_required=transport_required,
        )
        before = (place.place_layer, place.route_policy, place.tourist_eligible, place.transport_required, place.is_route_eligible)
        place.place_layer = classification.layer
        place.route_policy = classification.route_policy
        place.tourist_eligible = classification.tourist_eligible
        place.transport_required = transport_required
        if classification.route_exclusion_reason:
            place.route_exclusion_reason = classification.route_exclusion_reason
        place.is_route_eligible = bool(place.is_route_eligible and classification.is_route_eligible and not transport_required)
        after = (place.place_layer, place.route_policy, place.tourist_eligible, place.transport_required, place.is_route_eligible)
        counters[classification.layer] += 1
        if before != after:
            updated += 1
    db.flush()
    return {"updated": updated, "layers": dict(counters)}


def _tags(raw_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        return {}
    tags = raw_payload.get("tags")
    return tags if isinstance(tags, dict) else {}
