"""Reconcile an already-published place after category or verification metadata changes."""

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
    lock_place: bool = False,
) -> str:
    """Re-evaluate publication and route flags without committing."""

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
            lock_place=lock_place,
        )
        return "moved_to_review"

    apply_admin_city_publication_place(
        db,
        place,
        actor=actor,
        source=source,
        reason=reason,
        lock_place=lock_place,
    )
    return "reconciled_published"
