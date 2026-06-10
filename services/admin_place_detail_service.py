"""Детальная карточка места для админки."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.place import Place
from models.place_tag import PlaceTag
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_place_by_id


def build_admin_place_detail(db: Session, place_id: int) -> dict[str, object] | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None
    city = db.query(City).filter(City.id == place.city_id).first()
    tags = [
        {"id": t.id, "code": t.code, "name": t.name}
        for t in db.query(Tag).join(PlaceTag, PlaceTag.tag_id == Tag.id).filter(PlaceTag.place_id == place.id).all()
    ]
    route_usage = int(db.query(RoutePlace).filter(RoutePlace.place_id == place.id).count())
    audit = db.query(AdminAuditLog).filter(
        AdminAuditLog.entity_type == "place", AdminAuditLog.entity_id == str(place.id),
    ).order_by(AdminAuditLog.created_at.desc()).limit(20).all()
    return {
        "id": place.id, "slug": place.slug, "title": place.title,
        "city_id": place.city_id, "city_slug": city.slug if city else None, "city_name": city.name if city else None,
        "category": place.category, "tags": tags,
        "address": place.address, "address_source": place.address_source,
        "address_confidence": place.address_confidence, "address_updated_at": place.address_updated_at,
        "lat": place.lat, "lng": place.lng, "short_description": place.short_description,
        "image_url": place.image_url, "source": place.source, "source_url": place.source_url,
        "publication_status": place.publication_status, "verification_status": place.verification_status,
        "visible_to_users": place.is_visible_in_catalog, "route_enabled": place.is_route_eligible,
        "route_exclusion_reason": place.route_exclusion_reason,
        "existence_confidence_level": place.existence_confidence_level,
        "existence_confidence_score": place.existence_confidence_score,
        "admin_comment": place.admin_comment,
        "created_at": place.created_at, "updated_at": place.updated_at,
        "route_usage_count": route_usage,
        "route_usage_note": "Счётчик по шаблонным маршрутам в БД. Динамические построения — в product_events.",
        "audit_history": [
            {"id": a.id, "action": a.action, "actor": a.actor, "reason": a.reason, "created_at": a.created_at}
            for a in audit
        ],
    }
