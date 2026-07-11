from __future__ import annotations

import json
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts import import_city_osm as legacy_import
from db.session import SessionLocal
from models.city import City
from models.import_batch import ImportBatch
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from services.coverage_profile_filters import COVERAGE_PROFILE_FILTERS
from services.data_coverage_assurance import run_data_coverage_assurance
from services.osm_import_taxonomy import category_from_osm_tags
from services.place_layer_service import apply_place_layers
from services.import_pipeline.schema_compat import ensure_import_pipeline_schema

# These filters are the production Overpass contract for Data Coverage Assurance.
# The legacy importer still owns persistence/lifecycle logic; this wrapper installs
# the expanded tag selection and shared taxonomy before running it.
COVERAGE_AWARE_PROFILE_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "tourist_core": [
        ("tourism", "attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park"),
        ("historic", None),
        ("heritage", None),
        ("amenity", "cafe|restaurant|place_of_worship|monastery|marketplace"),
        ("amenity", "cafe|restaurant|place_of_worship|monastery"),
        ("amenity", "marketplace"),
        ("building", "church|cathedral|monastery|chapel|synagogue|mosque"),
        ("building", "church|cathedral|monastery|chapel"),
        ("building", "synagogue|mosque"),
        ("leisure", "park|garden|nature_reserve|playground|amusement_arcade|marina|promenade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("natural", "volcano|cliff|ridge"),
        ("waterway", "waterfall|river|stream"),
        ("waterway", "waterfall"),
        ("waterway", "river|stream"),
        ("attraction", "amusement_ride"),
        ("railway", "funicular|tram|monorail"),
        ("aerialway", "cable_car|gondola"),
        ("boundary", "national_park"),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "food_and_coffee": [
        ("amenity", "cafe|restaurant|fast_food|bar|pub|food_court|marketplace"),
        ("shop", "bakery|confectionery|coffee|tea|ice_cream|deli|cheese|pastry|marketplace"),
        ("cuisine", None),
    ],
    "nature_walk": [
        ("leisure", "park|garden|nature_reserve|playground|marina|promenade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("natural", "volcano|cliff|ridge"),
        ("waterway", "waterfall|river|stream"),
        ("waterway", "waterfall"),
        ("waterway", "river|stream"),
        ("tourism", "viewpoint|information|attraction"),
        ("boundary", "national_park"),
        ("heritage", None),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "useful_services": [
        ("amenity", "toilets|pharmacy|atm|shelter|clinic|hospital|police"),
    ],
}
COVERAGE_AWARE_PROFILE_FILTERS.update(COVERAGE_PROFILE_FILTERS)

_CURRENT_PROFILE: ContextVar[str | None] = ContextVar("osm_import_profile", default=None)
_DESTRUCTIVE_REJECTION_REASONS = {
    "source_closed",
    "source_temporarily_closed",
    "source_removed_from_source",
}


def _install_coverage_taxonomy(profile: str) -> None:
    legacy_import.PROFILE_FILTERS = COVERAGE_AWARE_PROFILE_FILTERS
    legacy_import._category = category_from_osm_tags
    legacy_import._ensure_source_presence = _ensure_source_presence_profile_safe
    legacy_import._mark_missing_sources = _mark_missing_sources_profile_safe
    legacy_import._hide_existing_rejected_place = _hide_existing_rejected_place_safe


def _hide_existing_rejected_place_safe(db, city_id: int, item: dict[str, Any]):
    """Only an explicit source lifecycle signal may hide an existing place.

    Taxonomy filtering, missing coordinates, and bad/missing names are evidence
    quality outcomes. They are not authoritative deletion signals.
    """
    reason = str(item.get("rejection_reason") or "rejected_import_object")
    if reason not in _DESTRUCTIVE_REJECTION_REASONS:
        return None
    place = (
        db.query(Place)
        .filter(Place.city_id == city_id, Place.source_url == item["source_url"])
        .first()
    )
    if place is None:
        return None
    return legacy_import.hide_place(
        place=place,
        reason=reason,
        status=legacy_import._status_for_rejection(reason),
    )


def _ensure_source_presence_profile_safe(
    db,
    place_id: int,
    source_external_id: str,
    source_observation_id: int | None,
    batch_id: int | None,
) -> None:
    profile = _CURRENT_PROFILE.get()
    if not profile:
        raise RuntimeError("OSM source profile context is missing; refusing unscoped presence write")

    existing = (
        db.query(PlaceSourcePresence)
        .filter_by(
            source_type="osm",
            source_profile=profile,
            source_external_id=source_external_id,
        )
        .first()
    )
    if existing is None:
        # Claim one legacy unscoped row on its first successful observation.
        # Other profiles get their own row, so overlapping OSM objects are safe.
        existing = (
            db.query(PlaceSourcePresence)
            .filter_by(
                source_type="osm",
                source_profile=None,
                source_external_id=source_external_id,
            )
            .first()
        )

    if existing is not None:
        existing.place_id = place_id
        existing.source_observation_id = source_observation_id
        existing.source_profile = profile
        existing.last_seen_at = datetime.utcnow()
        existing.last_seen_batch_id = batch_id
        existing.consecutive_missing_count = 0
        existing.last_missing_at = None
        existing.presence_status = "active_in_source"
        existing.updated_at = datetime.utcnow()
        return

    db.add(
        PlaceSourcePresence(
            place_id=place_id,
            source_observation_id=source_observation_id,
            source_type="osm",
            source_profile=profile,
            source_external_id=source_external_id,
            last_seen_batch_id=batch_id,
            presence_status="active_in_source",
        )
    )


def _mark_missing_sources_profile_safe(
    db,
    scope_id: int,
    batch_id: int,
    normalized: list[dict[str, Any]],
    city_admin_import_job_id: int | None,
) -> dict[str, int]:
    """Reconcile absence only inside the successfully fetched profile.

    The wrapper reaches this function only after Overpass returned and the raw
    object-limit check passed. Legacy rows without profile ownership are skipped
    fail-closed until a successful observation assigns them to a profile.
    """
    profile = _CURRENT_PROFILE.get()
    if not profile:
        raise RuntimeError("OSM source profile context is missing; refusing absence reconciliation")

    seen = {item["source_external_id"] for item in normalized}
    rows = (
        db.query(PlaceSourcePresence)
        .join(PlaceScopeLink, PlaceScopeLink.place_id == PlaceSourcePresence.place_id)
        .filter(
            PlaceScopeLink.scope_id == scope_id,
            PlaceSourcePresence.source_type == "osm",
            PlaceSourcePresence.source_profile == profile,
        )
        .all()
    )
    legacy_unscoped_skipped = (
        db.query(PlaceSourcePresence)
        .join(PlaceScopeLink, PlaceScopeLink.place_id == PlaceSourcePresence.place_id)
        .filter(
            PlaceScopeLink.scope_id == scope_id,
            PlaceSourcePresence.source_type == "osm",
            PlaceSourcePresence.source_profile.is_(None),
        )
        .count()
    )

    missing_rows = [row for row in rows if row.source_external_id not in seen]
    hidden_missing_places = 0
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).one()

    for row in missing_rows:
        row.consecutive_missing_count += 1
        row.last_missing_at = datetime.utcnow()
        row.presence_status = legacy_import._presence_status(row.consecutive_missing_count)
        row.last_seen_batch_id = row.last_seen_batch_id or batch_id
        row.updated_at = datetime.utcnow()

        if row.place_id is None:
            continue
        place = db.query(Place).filter(Place.id == row.place_id).first()
        if place is None:
            continue

        before_public = legacy_import._public_state_snapshot(place)
        decision = legacy_import.mark_missing_place(
            place=place,
            missing_count=row.consecutive_missing_count,
        )
        if decision.action == "hidden":
            hidden_missing_places += 1
            city = db.query(City).filter(City.id == place.city_id).first()
            if city is not None:
                legacy_import._enqueue_place_change_review(
                    db,
                    city=city,
                    batch=batch,
                    city_admin_import_job_id=city_admin_import_job_id,
                    place=place,
                    decision=decision,
                    item={"source_url": None},
                    before_public=before_public,
                )

    return {
        "missing_from_source": len(missing_rows),
        "hidden_missing_places": hidden_missing_places,
        "needs_review": hidden_missing_places,
        "legacy_unscoped_skipped": legacy_unscoped_skipped,
    }


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = legacy_import.parse_args(argv)
    token = _CURRENT_PROFILE.set(args.profile)
    try:
        _install_coverage_taxonomy(args.profile)
        if args.apply:
            with SessionLocal() as db:
                ensure_import_pipeline_schema(db.get_bind().engine)
        result = legacy_import.run(argv)

        if args.apply:
            with SessionLocal() as db:
                layer_result = apply_place_layers(db, city_slug=args.city)
                coverage = run_data_coverage_assurance(db, city_slug=args.city)
                db.commit()
            result = {
                **result,
                "reconciliation_contract": {
                    "scope": "profile",
                    "profile": args.profile,
                    "authoritative_fetch_required": True,
                    "legacy_unscoped_policy": "skip_until_seen",
                },
                "coverage_bridge": {"place_layers": layer_result},
                "data_coverage_assurance": {
                    "evaluated": coverage["evaluated"],
                    "changed": coverage["changed"],
                    "changed_by_assurance": coverage["changed_by_assurance"],
                    "summary": coverage["summary"],
                    "acceptance": coverage["acceptance"],
                    "recommended_actions": coverage["recommended_actions"],
                    "scope_suggestions": coverage.get("scope_suggestions", []),
                },
            }

        return result
    finally:
        _CURRENT_PROFILE.reset(token)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
