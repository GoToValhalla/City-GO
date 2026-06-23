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
    "title",
    "category",
    "canonical_category",
    "address",
    "short_description",
    "image_url",
    "lat",
    "lng",
    "source",
    "source_url",
    "website",
    "phone",
    "atmosphere",
    "inside",
    "best_for",
    "opening_hours",
    "average_visit_duration_minutes",
    "price_level",
    "indoor",
    "outdoor",
    "dog_friendly",
    "family_friendly",
    "is_active",
    "status",
    "publication_status",
    "verification_status",
    "admin_comment",
    "route_exclusion_reason",
    "address_source",
    "address_confidence",
})


def update_admin_place_fields(db: Session, place_id: int, fields: dict[str, object], *, actor: str) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None

    updates = dict(fields)
    reason = updates.pop("reason", None)
    if "category" in updates and "canonical_category" not in updates:
        category = updates.get("category")
        updates["canonical_category"] = str(category) if category else None

    if updates.get("lat") is not None and updates.get("lng") is not None:
        lat = float(updates["lat"])
        lng = float(updates["lng"])
        if abs(lat) < 0.000001 and abs(lng) < 0.000001:
            raise ValueError("Нельзя сохранить место с координатами 0,0")

    old = {key: getattr(place, key) for key in updates if key in _ALLOWED}
    for key, value in updates.items():
        if key in _ALLOWED:
            setattr(place, key, value)

    if "visible_to_users" in updates:
        place.is_visible_in_catalog = bool(updates["visible_to_users"])
    if "searchable" in updates:
        place.is_searchable = bool(updates["searchable"])
    if "route_enabled" in updates:
        place.is_route_eligible = bool(updates["route_enabled"])
        if updates["route_enabled"]:
            place.route_exclusion_reason = None
        elif updates.get("route_exclusion_reason"):
            place.route_exclusion_reason = str(updates["route_exclusion_reason"])
    if updates.get("publication_status") == "published":
        place.is_published = True
        place.published_at = datetime.utcnow()
    if updates.get("publication_status") in ("hidden", "unpublished", "draft", "needs_review"):
        place.is_published = False
    if "tag_ids" in updates:
        db.query(PlaceTag).filter(PlaceTag.place_id == place_id).delete()
        for tag_id in updates["tag_ids"] or []:
            db.add(PlaceTag(place_id=place_id, tag_id=int(tag_id)))

    write_admin_audit_log(
        db,
        actor=actor,
        action="update_place_admin",
        entity_type="place",
        entity_id=place.id,
        old_value=old,
        new_value=updates,
        reason=str(reason) if reason else None,
    )
    record_event(db, event_type="place_updated", place_id=place.id, commit=False)
    db.commit()
    db.refresh(place)
    return place
