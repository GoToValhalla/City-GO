from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.known_missing_poi import KnownMissingPoi
from models.place import Place

ALLOWED_STATUSES = {
    "missing",
    "matched",
    "needs_review",
    "source_absent",
    "out_of_scope",
    "tag_unsupported",
    "rejected_policy",
    "duplicate",
}

ALLOWED_GAP_REASONS = {
    None,
    "outside_bbox",
    "unsupported_tag",
    "source_absent",
    "hidden_by_policy",
    "missing_name",
    "missing_coordinates",
    "duplicate_candidate",
    "not_imported_scope",
    "not_visible_in_catalog",
    "not_route_eligible",
}


def update_coverage_gap_status(
    db: Session,
    *,
    gap_id: int,
    status: str | None = None,
    gap_reason: str | None = None,
    matched_place_id: int | None = None,
    review_notes: str | None = None,
    actor_id: str | None = None,
) -> KnownMissingPoi | None:
    """Updates one known-missing POI row from the admin Coverage Gaps UI.

    The automatic reconciliation service owns regular refreshes, but admins need an explicit
    override path for cases where the correct decision is editorial: mark source_absent,
    duplicate, needs_review or manually attach a matched place.
    """

    row = db.query(KnownMissingPoi).filter(KnownMissingPoi.id == gap_id).first()
    if row is None:
        return None

    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported coverage status: {status}")

    if gap_reason not in ALLOWED_GAP_REASONS:
        raise ValueError(f"Unsupported coverage gap reason: {gap_reason}")

    if matched_place_id is not None:
        place = db.query(Place).filter(Place.id == matched_place_id).first()
        if place is None:
            raise ValueError("Matched place not found")
        if place.city_id != row.city_id:
            raise ValueError("Matched place belongs to another city")
        row.matched_place_id = matched_place_id
        row.status = status or "matched"
        row.gap_reason = None if row.status == "matched" else gap_reason
        row.resolved_at = datetime.utcnow() if row.status == "matched" else None
    else:
        if status is not None:
            row.status = status
        row.gap_reason = gap_reason
        if status != "matched":
            row.resolved_at = None

    if review_notes is not None:
        prefix = f"[{actor_id or 'admin'}] "
        note = review_notes.strip()
        if note:
            row.review_notes = f"{prefix}{note}"

    row.last_checked_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.flush()
    return row


def coverage_gap_row_payload(row: KnownMissingPoi) -> dict[str, Any]:
    """Small response payload for admin actions without re-querying the full report."""

    city = row.city
    place = row.matched_place
    return {
        "id": row.id,
        "city_slug": city.slug if city else None,
        "slug": row.slug,
        "name": row.name_ru or row.name_en or row.name_local or row.slug,
        "status": row.status,
        "gap_reason": row.gap_reason,
        "review_notes": row.review_notes,
        "matched_place_id": row.matched_place_id,
        "matched_place_title": place.title if place else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
    }
