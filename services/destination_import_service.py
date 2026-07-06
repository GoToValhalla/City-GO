from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.city import City
from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.place import Place
from services.destination_candidate_adapter import DestinationCandidate, collect_scope_candidates
from services.destination_bbox import point_in_bbox
from services.destination_membership_service import upsert_membership
from services.destination_pipeline_counters import add_counter
from services.place_merge_policy import is_service_only_category


def import_destination_scope(db: Session, destination: Destination, scope: DestinationScope, counters: dict[str, int], *, dry_run: bool) -> list[Place]:
    candidates = collect_scope_candidates(destination, scope)
    counters["candidates_found"] += len(candidates)
    add_counter(counters, "scopes_processed")
    if dry_run:
        return []
    city_id = _city_id(db, destination, scope)
    if city_id is None:
        add_counter(counters, "errors_count")
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
    return Place(
        city_id=city_id,
        slug=candidate.slug,
        title=candidate.title,
        lat=candidate.lat,
        lng=candidate.lng,
        category=candidate.category,
        canonical_category=candidate.category,
        source=candidate.source,
        is_active=True,
        is_published=not service_only,
        is_visible_in_catalog=not service_only,
        is_route_eligible=not service_only,
        is_searchable=not service_only,
        publication_status="published" if not service_only else "hidden",
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
