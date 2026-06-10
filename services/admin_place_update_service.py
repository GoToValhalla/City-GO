"""Обновление места из админки."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.place_service import get_place_by_id
from services.product_event_service import record_event

_ALLOWED = frozenset({
    "title", "category", "address", "short_description", "lat", "lng", "source",
    "publication_status", "verification_status", "admin_comment", "route_exclusion_reason",
    "address_source", "address_confidence",
})


def update_admin_place_fields(db: Session, place_id: int, fields: dict[str, object], *, actor: str) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    old = {k: getattr(place, k) for k in fields if k in _ALLOWED}
    for key, value in fields.items():
        if key in _ALLOWED:
            setattr(place, key, value)
    if "visible_to_users" in fields:
        place.is_visible_in_catalog = bool(fields["visible_to_users"])
    if "route_enabled" in fields:
        place.is_route_eligible = bool(fields["route_enabled"])
        if not fields["route_enabled"] and fields.get("route_exclusion_reason"):
            place.route_exclusion_reason = str(fields["route_exclusion_reason"])
    if fields.get("publication_status") == "published":
        place.is_published = True
        place.published_at = datetime.utcnow()
    if fields.get("publication_status") in ("hidden", "unpublished", "draft"):
        place.is_published = False
    if "tag_ids" in fields:
        db.query(PlaceTag).filter(PlaceTag.place_id == place_id).delete()
        for tid in fields["tag_ids"] or []:
            db.add(PlaceTag(place_id=place_id, tag_id=int(tid)))
    write_admin_audit_log(db, actor=actor, action="update_place_admin", entity_type="place", entity_id=place.id,
                          old_value=old, new_value=fields, reason=fields.get("reason"))
    record_event(db, event_type="place_updated", place_id=place.id, commit=False)
    db.commit()
    db.refresh(place)
    return place
