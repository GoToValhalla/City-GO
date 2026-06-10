"""Фильтры и preset'ы списка мест в админке."""

from __future__ import annotations

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place

JUNK_CATEGORIES = ("service", "pharmacy", "hospital", "parking", "atm", "fuel")
SERVICE_KEYWORDS = ("аптек", "больниц", "парков", "стоянк", "pharmacy", "hospital", "parking")


def apply_place_preset(query: Query, preset: str) -> Query:
    rules = {
        "no_photo": lambda q: q.filter(Place.image_url.is_(None)),
        "no_address": lambda q: q.filter(or_(Place.address.is_(None), Place.address == "")),
        "no_description": lambda q: q.filter(or_(Place.short_description.is_(None), Place.short_description == "")),
        "low_confidence": lambda q: q.filter(Place.existence_confidence_level.in_(("low", "unknown"))),
        "needs_review": lambda q: q.filter(Place.verification_status.in_(("needs_recheck", "unverified"))),
        "not_in_routes": lambda q: q.filter(Place.is_route_eligible.is_(False)),
        "in_routes": lambda q: q.filter(Place.is_route_eligible.is_(True), Place.is_published.is_(True)),
        "junk_categories": lambda q: q.filter(Place.category.in_(JUNK_CATEGORIES)),
        "problematic": lambda q: q.filter(or_(
            Place.image_url.is_(None),
            Place.address.is_(None),
            Place.existence_confidence_level.in_(("low", "unknown")),
            Place.verification_status.in_(("needs_recheck", "unverified")),
        )),
    }
    if preset == "suspicious_names":
        return query.filter(or_(Place.title.ilike("%???%"), Place.title.ilike("%test%"), Place.title.ilike("%тест%")))
    if preset == "service_places":
        clauses = [Place.category.in_(JUNK_CATEGORIES)]
        clauses.extend(Place.title.ilike(f"%{kw}%") for kw in SERVICE_KEYWORDS)
        return query.filter(or_(*clauses))
    fn = rules.get(preset)
    return fn(query) if fn else query


def apply_place_filters(
    db: Session,
    query: Query,
    *,
    city_slug: str | None = None,
    publication_status: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    q: str | None = None,
    preset: str | None = None,
    has_photo: bool | None = None,
    has_address: bool | None = None,
    has_description: bool | None = None,
    route_eligible: bool | None = None,
    low_confidence: bool | None = None,
    source: str | None = None,
) -> Query:
    if city_slug:
        query = query.join(City).filter(City.slug == city_slug)
    if publication_status:
        query = query.filter(Place.publication_status == publication_status)
    if verification_status:
        query = query.filter(Place.verification_status == verification_status)
    if category:
        query = query.filter(Place.category == category)
    if q:
        query = query.filter(Place.title.ilike(f"%{q.strip()}%"))
    if has_photo is True:
        query = query.filter(Place.image_url.isnot(None))
    elif has_photo is False:
        query = query.filter(Place.image_url.is_(None))
    if has_address is True:
        query = query.filter(Place.address.isnot(None), Place.address != "")
    elif has_address is False:
        query = query.filter(or_(Place.address.is_(None), Place.address == ""))
    if has_description is True:
        query = query.filter(Place.short_description.isnot(None), Place.short_description != "")
    elif has_description is False:
        query = query.filter(or_(Place.short_description.is_(None), Place.short_description == ""))
    if route_eligible is not None:
        query = query.filter(Place.is_route_eligible.is_(route_eligible))
    if low_confidence:
        query = query.filter(Place.existence_confidence_level.in_(("low", "unknown")))
    if source:
        query = query.filter(Place.source == source)
    if preset:
        query = apply_place_preset(query, preset)
    return query
