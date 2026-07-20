"""Reconcile RouteDraft points against the live public route contract."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.route_draft import RouteDraft
from services.route_draft_rules import eligible_place_query, warning


def reconcile_draft_public_points(db: Session, draft: RouteDraft) -> bool:
    """Drop points that no longer satisfy the public contract. Returns True if changed."""
    place_ids = {int(item.place_id) for item in draft.points}
    if not place_ids:
        return False
    eligible = {
        int(row.id)
        for row in eligible_place_query(db.query(Place), draft.city_id).filter(Place.id.in_(place_ids)).all()
    }
    stale = [item for item in list(draft.points) if int(item.place_id) not in eligible]
    if not stale:
        return False
    for item in stale:
        db.delete(item)
    kept = [item for item in draft.points if int(item.place_id) in eligible]
    for index, item in enumerate(sorted(kept, key=lambda row: row.position), start=1):
        item.position = index
    draft.points = kept
    draft.warnings = list(draft.warnings or []) + [
        warning("STALE_POINTS_REMOVED", "Некоторые точки больше недоступны для публичного маршрута.")
    ]
    return True
