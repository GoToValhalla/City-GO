from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.city import City
from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.place import Place
from services.destination_candidate_adapter import DestinationCandidate, DestinationSourceError, collect_scope_candidates
from services.destination_bbox import point_in_bbox
from services.destination_membership_service import upsert_membership
from services.destination_pipeline_counters import add_counter
from services.place_merge_policy import is_service_only_category
from services.publication_state_writer import REASON_NON_PUBLIC_CATEGORY, REASON_PUBLISHED, transition_place_publication


def import_destination_scope(db: Session, destination: Destination, scope: DestinationScope, counters: dict[str, int], *, dry_run: bool, errors: list[dict[str, object]] | None = None) -> list[Place]:
    try:
        candidates = collect_scope_candidates(destination, scope)
    except DestinationSourceError as exc:
        add_counter(counters, "errors_count")
        add_counter(counters, "source_errors")
        if errors is not None:
            errors.append({"stage": "importing", "scope_code": scope.code, "message": str(exc)[:500]})
        return []
    counters["candidates_found"] += len(candidates)
    add_counter(counters, "scopes_processed")
    if dry_run:
        return []
    city_id = _city_id(db, destination, scope)
    if city_id is None:
        add_counter(counters, "errors_count")
        if errors is not None:
            errors.append({"stage": "importing", "scope_code": scope.code, "message": "Не найден активный город для записи мест"})
        return []
    places = [_upsert_candidate(db, city_id, destination, scope, candidate, counters) for candidate in candidates]
    scope.last_imported_at = datetime.now(timezone.utc)
    return places


def _upsert_candidate(db: Session, city_id: int, destination: Destination, scope: DestinationScope, candidate: DestinationCandidate, counters: dict[str, int]) -> Place:
    place = db.query(Place).filter(Place.city_id == city_id, Place.slug == candidate.slug).first()
    service_only = is_service_only_category(candidate.category)
    if place is None:
        place = _new_place(city_id, candidate, service_only)
        db.add(place)
        db.flush()
        transition_place_publication(
            db,
            place,
            to_status="hidden" if service_only else "published",
            reason_code=REASON_NON_PUBLIC_CATEGORY if service_only else REASON_PUBLISHED,
            actor="destination_import",
            source="destination_import",
            reason_details={"service_only": service_only, "destination_id": destination.id, "scope_id": scope.id},
            route_eligible_when_published=not service_only,
            lock_place=False,
        )
        add_counter(counters, "places_created")
    else:
        add_counter(counters, "duplicates_skipped")
    before = _membership_exists(db, place.id, destination.id)
    upsert_membership(db, place_id=place.id, destination_id=destination.id, assignment_type="imported", is_primary=not service_only, confidence=0.86, source=candidate.source, scope_id=scope.id)
    add_counter(counters, "memberships_updated" if before else "memberships_created")
    if service_only:
        add_counter(counters, "service_only_hidden")
    return place


def _new_place(city_id: int, candidate: DestinationCandidate, service_only: bool) -> Place:
    """Construct a brand-new destination place with no publication state set.

    Controlled publication fields (is_active/is_published/is_visible_in_catalog/
    is_route_eligible/is_searchable/publication_status/...) are never set here:
    the canonical writer (transition_place_publication, called by the caller
    right after db.flush()) is the only owner of that state, and drives the
    place to the same end state as before (published, or hidden for
    service_only categories) through an audited transition instead of a
    direct, ungated, unattributed constructor bypass."""
    changes = candidate.changes or {}
    return Place(
        city_id=city_id,
        slug=candidate.slug,
        title=candidate.title,
        lat=candidate.lat,
        lng=candidate.lng,
        category=candidate.category,
        canonical_category=candidate.category,
        short_description=changes.get("short_description") if isinstance(changes.get("short_description"), str) else None,
        address=changes.get("address") if isinstance(changes.get("address"), str) else None,
        opening_hours=changes.get("opening_hours"),
        average_visit_duration_minutes=changes.get("average_visit_duration_minutes") if isinstance(changes.get("average_visit_duration_minutes"), int) else None,
        source=candidate.source,
        internal_status="service_only" if service_only else "active",
    )


def _membership_exists(db: Session, place_id: int, destination_id: int) -> bool:
    return db.query(DestinationPlaceMembership.id).filter_by(place_id=place_id, destination_id=destination_id).first() is not None


def _city_id(db: Session, destination: Destination, scope: DestinationScope) -> int | None:
    if destination.legacy_city_id:
        return int(destination.legacy_city_id)
    bbox = scope.bbox or destination.bbox
    city = db.query(City).filter(City.is_active.is_(True)).all()
    match = next((row for row in city if row.center_lat and row.center_lng and point_in_bbox(row.center_lat, row.center_lng, bbox)), None)
    return int(match.id) if match else None
