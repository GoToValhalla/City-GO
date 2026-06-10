"""Список мест для Eligibility Dashboard."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.place_quality_score import compute_place_quality_score, quality_bucket
from services.route_eligibility import evaluate_place_route_eligibility
from services.route_eligibility_dashboard.reasons import dashboard_reasons, primary_reason


def list_eligibility_places(
    db: Session,
    *,
    city_slug: str | None = None,
    category: str | None = None,
    eligible: bool | None = None,
    no_photo: bool | None = None,
    no_address: bool | None = None,
    no_description: bool | None = None,
    unpublished: bool | None = None,
    inactive: bool | None = None,
    issue: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    city = _resolve_city(db, city_slug)
    query = db.query(Place)
    if city is not None:
        query = query.filter(Place.city_id == city.id)
    query = _apply_filters(
        query, category=category, no_photo=no_photo, no_address=no_address,
        no_description=no_description, unpublished=unpublished, inactive=inactive,
    )
    rows = query.order_by(Place.id.desc()).limit(1000).all()
    items = [_row(place, city) for place in rows]
    if eligible is not None:
        items = [row for row in items if row["eligible"] is eligible]
    if issue:
        items = [row for row in items if issue in row["reasons"] or row["primary_reason"] == issue]
    total = len(items)
    return items[offset : offset + min(limit, 200)], total


def _row(place: Place, city: City | None) -> dict[str, object]:
    result = evaluate_place_route_eligibility(place, city=city)
    score = compute_place_quality_score(place)
    reasons = dashboard_reasons(place, city=city)
    return {
        "place_id": place.id,
        "title": place.title,
        "slug": place.slug,
        "category": place.category,
        "eligible": result.eligible,
        "quality_score": score,
        "quality_bucket": quality_bucket(score),
        "reasons": reasons,
        "primary_reason": primary_reason(reasons),
        "city_slug": city.slug if city else None,
    }


def _resolve_city(db: Session, city_slug: str | None) -> City | None:
    if not city_slug:
        return None
    return db.query(City).filter(City.slug == city_slug).first()


def _apply_filters(
    query: Query,
    *,
    category: str | None,
    no_photo: bool | None,
    no_address: bool | None,
    no_description: bool | None,
    unpublished: bool | None,
    inactive: bool | None,
) -> Query:
    if category:
        query = query.filter(Place.category == category)
    if no_photo:
        query = query.filter(Place.image_url.is_(None))
    if no_address:
        query = query.filter(or_(Place.address.is_(None), Place.address == ""))
    if no_description:
        query = query.filter(or_(Place.short_description.is_(None), Place.short_description == ""))
    if unpublished:
        query = query.filter(Place.is_published.is_(False))
    if inactive:
        query = query.filter(or_(Place.is_active.is_(False), Place.status != "active"))
    return query
