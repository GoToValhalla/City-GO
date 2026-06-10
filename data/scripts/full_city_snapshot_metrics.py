"""Метрики снимка города для full import audit."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from models.place import Place
from services.admin_coverage_place_checks import place_has_coverage_address, place_has_coverage_description
from services.city_slug_resolver import resolve_city_by_slug
from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES
from services.place_public_image_service import resolve_public_place_images_bulk
from services.route_eligibility import route_eligible_sql_conditions


def snapshot_city(db: Session, city_slug: str) -> dict[str, object]:
    city = resolve_city_by_slug(db, city_slug)
    if city is None:
        return {"city_slug": city_slug, "error": "city_not_found"}
    base = db.query(Place).filter(Place.city_id == city.id)
    published = base.filter(Place.is_published.is_(True)).all()
    pub_images = resolve_public_place_images_bulk(db, published)
    categories: Counter[str] = Counter()
    for (category,) in base.with_entities(Place.category).all():
        categories[str(category or "unknown")] += 1
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "launch_status": city.launch_status,
        "places_total": base.count(),
        "places_published": len(published),
        "places_unpublished": base.filter(Place.is_published.is_(False)).count(),
        "places_active": base.filter(Place.is_active.is_(True)).count(),
        "places_with_real_address": sum(1 for p in published if place_has_coverage_address(p)),
        "places_without_real_address": sum(1 for p in published if not place_has_coverage_address(p)),
        "places_with_description": sum(1 for p in published if place_has_coverage_description(p)),
        "places_without_description": sum(1 for p in published if not place_has_coverage_description(p)),
        "places_with_public_photo": sum(1 for p in published if pub_images.get(p.id) is not None),
        "places_without_public_photo": sum(1 for p in published if pub_images.get(p.id) is None),
        "places_route_eligible": base.filter(*route_eligible_sql_conditions()).count(),
        "places_forbidden_or_hidden_category": base.filter(Place.category.in_(tuple(PUBLIC_HIDDEN_CATEGORIES))).count(),
        "category_counts": dict(sorted(categories.items(), key=lambda item: (-item[1], item[0]))),
        "hidden_category_breakdown": {cat: categories.get(cat, 0) for cat in sorted(PUBLIC_HIDDEN_CATEGORIES)},
    }


def snapshot_all_cities(db: Session, city_slugs: list[str]) -> list[dict[str, object]]:
    return [snapshot_city(db, slug) for slug in city_slugs]
