from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.city_import_scope import CityImportScope
from models.city_scope_import_state import CityScopeImportState
from models.import_batch import ImportBatch
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=False, help="Filter by city slug")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)

    with SessionLocal() as db:
        cities_query = db.query(City).order_by(City.slug)

        if args.city:
            cities_query = cities_query.filter(City.slug == args.city)

        cities = cities_query.all()

        result = {
            "checked_at": datetime.utcnow().isoformat(),
            "city_count": len(cities),
            "cities": [],
        }

        for city in cities:
            result["cities"].append(_city_status(db, city))

        return result


def _city_status(db, city: City) -> dict[str, Any]:
    scopes = (
        db.query(CityImportScope)
        .filter(CityImportScope.city_id == city.id)
        .order_by(CityImportScope.code)
        .all()
    )

    places_count = _count(db, Place, Place.city_id == city.id)
    active_places_count = _count(
        db,
        Place,
        Place.city_id == city.id,
        Place.is_active.is_(True),
        Place.status == "active",
    )

    source_observations_count = _count(db, SourceObservation, SourceObservation.city_id == city.id)
    batches_count = _count(db, ImportBatch, ImportBatch.city_id == city.id)

    places_by_category = _places_by_category(db, city.id)
    batches_by_status = _batches_by_status(db, city.id)
    observations_by_status = _observations_by_status(db, city.id)

    return {
        "city": {
            "id": city.id,
            "slug": city.slug,
            "name": city.name,
            "country": city.country,
            "region": city.region,
            "launch_status": city.launch_status,
            "is_active": city.is_active,
            "timezone": city.timezone,
        },
        "totals": {
            "places": places_count,
            "active_places": active_places_count,
            "source_observations": source_observations_count,
            "import_batches": batches_count,
            "scopes": len(scopes),
        },
        "places_by_category": places_by_category,
        "batches_by_status": batches_by_status,
        "observations_by_status": observations_by_status,
        "scopes": [_scope_status(db, city.id, scope) for scope in scopes],
    }


def _scope_status(db, city_id: int, scope: CityImportScope) -> dict[str, Any]:
    places_in_scope = (
        db.query(func.count(PlaceScopeLink.place_id))
        .filter(PlaceScopeLink.scope_id == scope.id)
        .scalar()
        or 0
    )

    observations_count = _count(
        db,
        SourceObservation,
        SourceObservation.city_id == city_id,
        SourceObservation.scope_id == scope.id,
    )

    rejected_observations_count = _count(
        db,
        SourceObservation,
        SourceObservation.city_id == city_id,
        SourceObservation.scope_id == scope.id,
        SourceObservation.normalization_status == "rejected",
    )

    linked_observations_count = _count(
        db,
        SourceObservation,
        SourceObservation.city_id == city_id,
        SourceObservation.scope_id == scope.id,
        SourceObservation.normalization_status == "linked_to_place",
    )

    batches_count = _count(
        db,
        ImportBatch,
        ImportBatch.city_id == city_id,
        ImportBatch.scope_id == scope.id,
    )

    last_batch = (
        db.query(ImportBatch)
        .filter(
            ImportBatch.city_id == city_id,
            ImportBatch.scope_id == scope.id,
        )
        .order_by(ImportBatch.id.desc())
        .first()
    )

    import_state = (
        db.query(CityScopeImportState)
        .filter(
            CityScopeImportState.city_id == city_id,
            CityScopeImportState.scope_id == scope.id,
        )
        .order_by(CityScopeImportState.id.desc())
        .first()
    )

    presence_summary = _source_presence_summary(db, scope.id)

    return {
        "id": scope.id,
        "code": scope.code,
        "name": scope.name,
        "enabled": scope.enabled,
        "status": scope.status,
        "import_profile": scope.import_profile,
        "refresh_interval_hours": scope.refresh_interval_hours,
        "last_imported_at": _dt(scope.last_imported_at),
        "next_run_at": _dt(scope.next_run_at),
        "locked_at": _dt(getattr(scope, "locked_at", None)),
        "bbox": scope.bbox,
        "totals": {
            "places_linked_to_scope": places_in_scope,
            "source_observations": observations_count,
            "linked_observations": linked_observations_count,
            "rejected_observations": rejected_observations_count,
            "import_batches": batches_count,
        },
        "source_presence": presence_summary,
        "last_batch": _batch_summary(last_batch),
        "import_state": _import_state_summary(import_state),
    }


def _places_by_category(db, city_id: int) -> dict[str, int]:
    rows = (
        db.query(Place.category, func.count(Place.id))
        .filter(Place.city_id == city_id)
        .group_by(Place.category)
        .order_by(Place.category)
        .all()
    )

    return {str(category or "unknown"): int(count) for category, count in rows}


def _batches_by_status(db, city_id: int) -> dict[str, int]:
    rows = (
        db.query(ImportBatch.status, func.count(ImportBatch.id))
        .filter(ImportBatch.city_id == city_id)
        .group_by(ImportBatch.status)
        .order_by(ImportBatch.status)
        .all()
    )

    return {str(status or "unknown"): int(count) for status, count in rows}


def _observations_by_status(db, city_id: int) -> dict[str, int]:
    rows = (
        db.query(SourceObservation.normalization_status, func.count(SourceObservation.id))
        .filter(SourceObservation.city_id == city_id)
        .group_by(SourceObservation.normalization_status)
        .order_by(SourceObservation.normalization_status)
        .all()
    )

    return {str(status or "unknown"): int(count) for status, count in rows}


def _source_presence_summary(db, scope_id: int) -> dict[str, int]:
    rows = (
        db.query(PlaceSourcePresence.presence_status, func.count(PlaceSourcePresence.id))
        .join(SourceObservation, SourceObservation.id == PlaceSourcePresence.source_observation_id)
        .filter(SourceObservation.scope_id == scope_id)
        .group_by(PlaceSourcePresence.presence_status)
        .order_by(PlaceSourcePresence.presence_status)
        .all()
    )

    return {str(status or "unknown"): int(count) for status, count in rows}


def _batch_summary(batch: ImportBatch | None) -> dict[str, Any] | None:
    if batch is None:
        return None

    return {
        "id": batch.id,
        "source_type": batch.source_type,
        "mode": batch.mode,
        "status": batch.status,
        "dry_run": batch.dry_run,
        "started_at": _dt(batch.started_at),
        "finished_at": _dt(batch.finished_at),
        "raw_count": batch.raw_count,
        "normalized_count": batch.normalized_count,
        "published_count": batch.published_count,
        "needs_review_count": batch.needs_review_count,
        "rejected_count": batch.rejected_count,
        "duplicate_count": batch.duplicate_count,
        "errors_count": batch.errors_count,
        "diff_summary": batch.diff_summary,
    }


def _import_state_summary(state: CityScopeImportState | None) -> dict[str, Any] | None:
    if state is None:
        return None

    return {
        "id": state.id,
        "source_type": state.source_type,
        "import_profile": state.import_profile,
        "last_status": state.last_status,
        "coverage_status": state.coverage_status,
        "coverage_score": state.coverage_score,
        "last_successful_batch_id": state.last_successful_batch_id,
        "last_attempted_batch_id": state.last_attempted_batch_id,
        "last_started_at": _dt(state.last_started_at),
        "last_finished_at": _dt(state.last_finished_at),
        "last_error": state.last_error,
        "last_raw_count": state.last_raw_count,
        "last_normalized_count": state.last_normalized_count,
        "last_published_count": state.last_published_count,
        "last_needs_review_count": state.last_needs_review_count,
        "last_rejected_count": state.last_rejected_count,
        "last_duplicate_count": state.last_duplicate_count,
        "last_missing_from_source_count": state.last_missing_from_source_count,
        "next_run_at": _dt(state.next_run_at),
    }


def _count(db, model, *filters) -> int:
    query = db.query(func.count(model.id))

    for filter_item in filters:
        query = query.filter(filter_item)

    return int(query.scalar() or 0)


def _dt(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def print_text_report(data: dict[str, Any]) -> None:
    print(f"Checked at: {data['checked_at']}")
    print(f"Cities: {data['city_count']}")
    print("")

    for item in data["cities"]:
        city = item["city"]
        totals = item["totals"]

        print("=" * 90)
        print(f"{city['slug']} — {city['name']}")
        print(f"Country/region: {city['country']} / {city['region']}")
        print(f"Status: launch_status={city['launch_status']} is_active={city['is_active']}")
        print(
            "Totals: "
            f"places={totals['places']} "
            f"active_places={totals['active_places']} "
            f"observations={totals['source_observations']} "
            f"batches={totals['import_batches']} "
            f"scopes={totals['scopes']}"
        )

        print("")
        print("Places by category:")
        if item["places_by_category"]:
            for category, count in item["places_by_category"].items():
                print(f"  - {category}: {count}")
        else:
            print("  - none")

        print("")
        print("Batches by status:")
        if item["batches_by_status"]:
            for status, count in item["batches_by_status"].items():
                print(f"  - {status}: {count}")
        else:
            print("  - none")

        print("")
        print("Scopes:")
        if not item["scopes"]:
            print("  - none")

        for scope in item["scopes"]:
            print(
                f"  - {scope['code']}: "
                f"status={scope['status']} "
                f"enabled={scope['enabled']} "
                f"profile={scope['import_profile']} "
                f"places={scope['totals']['places_linked_to_scope']} "
                f"observations={scope['totals']['source_observations']} "
                f"rejected={scope['totals']['rejected_observations']} "
                f"last_imported_at={scope['last_imported_at']}"
            )

            if scope["last_batch"]:
                batch = scope["last_batch"]
                print(
                    f"    last_batch id={batch['id']} "
                    f"status={batch['status']} "
                    f"raw={batch['raw_count']} "
                    f"normalized={batch['normalized_count']} "
                    f"published={batch['published_count']} "
                    f"rejected={batch['rejected_count']} "
                    f"errors={batch['errors_count']}"
                )

            if scope["import_state"]:
                state = scope["import_state"]
                print(
                    f"    import_state status={state['last_status']} "
                    f"coverage={state['coverage_status']} "
                    f"error={state['last_error']}"
                )

        print("")


if __name__ == "__main__":
    result = run()

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_text_report(result)