"""Детальная карточка места для админки."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
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
        {"id": tag.id, "code": tag.code, "name": tag.name}
        for tag in db.query(Tag).join(PlaceTag, PlaceTag.tag_id == Tag.id).filter(PlaceTag.place_id == place.id).all()
    ]
    route_usage = int(db.query(RoutePlace).filter(RoutePlace.place_id == place.id).count())
    audit = db.query(AdminAuditLog).filter(
        AdminAuditLog.entity_type == "place", AdminAuditLog.entity_id == str(place.id),
    ).order_by(AdminAuditLog.created_at.desc()).limit(20).all()
    return {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "city_id": place.city_id,
        "city_slug": city.slug if city else None,
        "city_name": city.name if city else None,
        "category": place.category,
        "canonical_category": place.canonical_category,
        "tags": tags,
        "address": place.address,
        "address_source": place.address_source,
        "address_confidence": place.address_confidence,
        "address_updated_at": place.address_updated_at,
        "lat": place.lat,
        "lng": place.lng,
        "short_description": place.short_description,
        "image_url": place.image_url,
        "source": place.source,
        "source_url": place.source_url,
        "website": place.website,
        "phone": place.phone,
        "atmosphere": place.atmosphere,
        "inside": place.inside,
        "best_for": place.best_for,
        "opening_hours": place.opening_hours,
        "average_visit_duration_minutes": place.average_visit_duration_minutes,
        "price_level": place.price_level,
        "indoor": place.indoor,
        "outdoor": place.outdoor,
        "dog_friendly": place.dog_friendly,
        "family_friendly": place.family_friendly,
        "is_active": place.is_active,
        "status": place.status,
        "lifecycle_status": place.lifecycle_status,
        "quality_tier": place.quality_tier,
        "quality_score": place.quality_score,
        "completeness_score": place.completeness_score,
        "photo_score": place.photo_score,
        "description_score": place.description_score,
        "confidence_score": place.confidence_score,
        "freshness_score": place.freshness_score,
        "publication_status": place.publication_status,
        "verification_status": place.verification_status,
        "visible_to_users": place.is_visible_in_catalog,
        "searchable": place.is_searchable,
        "route_enabled": place.is_route_eligible,
        "route_exclusion_reason": place.route_exclusion_reason,
        "existence_confidence_level": place.existence_confidence_level,
        "existence_confidence_score": place.existence_confidence_score,
        "admin_comment": place.admin_comment,
        "created_at": place.created_at,
        "updated_at": place.updated_at,
        "route_usage_count": route_usage,
        "route_usage_note": "Счётчик по шаблонным маршрутам в БД. Динамические построения учитываются отдельно.",
        "audit_history": [
            {
                "id": item.id,
                "action": item.action,
                "actor": item.actor,
                "reason": item.reason,
                "created_at": item.created_at,
            }
            for item in audit
        ],
    }
