"""Reconcile an already-published place after data or taxonomy changes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_publication_eligibility import place_publication_eligibility
from services.publication_reason_mapping import primary_publication_reason
from services.publication_state_writer import transition_place_publication


def reconcile_published_place(
    db: Session,
    place: Place,
    *,
    actor: str,
    source: str,
    reason: str,
    lock_place: bool = True,
) -> str:
    """Re-evaluate publication and route state without committing."""
    if lock_place:
        place = (
            db.query(Place)
            .filter(Place.id == place.id)
            .populate_existing()
            .with_for_update()
            .one()
        )

    if place.publication_status != "published" or not place.is_published:
        return "not_published"

    eligibility = place_publication_eligibility(place)
    if not eligibility.eligible:
        transition_place_publication(
            db,
            place,
            to_status="needs_review",
            reason_code=primary_publication_reason(eligibility.reasons),
            actor=actor,
            source=source,
            reason_details={"failed_gates": list(eligibility.reasons)},
            human_comment=reason,
            lock_place=False,
        )
        return "moved_to_review"

    before = (
        bool(place.is_active),
        bool(place.is_published),
        bool(place.is_visible_in_catalog),
        bool(place.is_searchable),
        bool(place.is_route_eligible),
        place.route_exclusion_reason,
        place.publication_reason_code,
        dict(place.publication_reason_details or {}),
        place.unpublished_at,
        place.published_at,
    )
    apply_admin_city_publication_place(
        db,
        place,
        actor=actor,
        source=source,
        reason=reason,
        lock_place=False,
    )
    after = (
        bool(place.is_active),
        bool(place.is_published),
        bool(place.is_visible_in_catalog),
        bool(place.is_searchable),
        bool(place.is_route_eligible),
        place.route_exclusion_reason,
        place.publication_reason_code,
        dict(place.publication_reason_details or {}),
        place.unpublished_at,
        place.published_at,
    )
    return "reconciled_published" if before != after else "unchanged"
