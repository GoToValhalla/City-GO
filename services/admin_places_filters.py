"""Фильтры и быстрые выборки списка мест в админке."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

# Реальные инфраструктурные категории не являются мусором. Здесь остаются только
# неразобранные общие значения, требующие нормализации.
JUNK_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES | {"unknown", "other", "useful"}))
SERVICE_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES))


def _search_terms(value: str) -> tuple[str, ...]:
    text = value.strip()
    variants = (text, text.casefold(), text.lower(), text.capitalize(), text.title(), text.upper())
    return tuple(dict.fromkeys(f"%{item}%" for item in variants if item))


def apply_place_preset(query: Query, preset: str) -> Query:
    rules = {
        "no_photo": lambda q: q.filter(or_(Place.image_url.is_(None), Place.image_url == "")),
        "no_address": lambda q: q.filter(or_(Place.address.is_(None), Place.address == "")),
        "no_description": lambda q: q.filter(or_(Place.short_description.is_(None), Place.short_description == "")),
        "no_contacts": lambda q: q.filter(or_(Place.phone.is_(None), Place.phone == ""), or_(Place.website.is_(None), Place.website == "")),
        "no_hours": lambda q: q.filter(Place.opening_hours.is_(None)),
        "low_confidence": lambda q: q.filter(Place.existence_confidence_level.in_(("low", "unknown"))),
        "needs_review": lambda q: q.filter(Place.verification_status.in_(("needs_recheck", "unverified"))),
        "not_in_routes": lambda q: q.filter(Place.is_route_eligible.is_not(True)),
        "route_unknown": lambda q: q.filter(Place.is_route_eligible.is_(None)),
        "in_routes": lambda q: q.filter(Place.is_route_eligible.is_(True), Place.is_published.is_(True)),
        "published_not_route_eligible": lambda q: q.filter(Place.is_published.is_(True), Place.is_route_eligible.is_not(True)),
        "route_eligible_no_photo": lambda q: q.filter(Place.is_route_eligible.is_(True), or_(Place.image_url.is_(None), Place.image_url == "")),
        "route_eligible_no_address": lambda q: q.filter(Place.is_route_eligible.is_(True), or_(Place.address.is_(None), Place.address == "")),
        "generic_osm_placeholders": lambda q: q.filter(_placeholder_clause()),
        "junk_categories": lambda q: q.filter(_canonical_category_clause(JUNK_CATEGORIES)),
        "service_places": lambda q: q.filter(_canonical_category_clause(SERVICE_CATEGORIES)),
        "problematic": lambda q: q.filter(or_(
            Place.image_url.is_(None),
            Place.address.is_(None),
            Place.short_description.is_(None),
            Place.existence_confidence_level.in_(("low", "unknown")),
            Place.verification_status.in_(("needs_recheck", "unverified")),
            Place.is_duplicate_suspected.is_(True),
            Place.is_spam_poi.is_(True),
        )),
    }
    if preset == "suspicious_names":
        return query.filter(or_(Place.title.ilike("%???%"), Place.title.ilike("%test%"), Place.title.ilike("%тест%")))
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
    has_phone: bool | None = None,
    has_website: bool | None = None,
    has_opening_hours: bool | None = None,
    route_eligible: bool | None = None,
    is_active: bool | None = None,
    searchable: bool | None = None,
    low_confidence: bool | None = None,
    quality_tier: str | None = None,
    source: str | None = None,
) -> Query:
    if city_slug:
        query = query.join(City).filter(City.slug == city_slug)
    if publication_status:
        query = query.filter(Place.publication_status == publication_status)
    if verification_status:
        query = query.filter(Place.verification_status == verification_status)
    if category:
        query = query.filter(or_(Place.canonical_category == category, Place.category == category))
    if q:
        clauses = tuple(or_(Place.title.ilike(term), Place.slug.ilike(term), Place.address.ilike(term)) for term in _search_terms(q))
        query = query.filter(or_(*clauses))
    query = _presence_filter(query, Place.image_url, has_photo)
    query = _presence_filter(query, Place.address, has_address)
    query = _presence_filter(query, Place.short_description, has_description)
    query = _presence_filter(query, Place.phone, has_phone)
    query = _presence_filter(query, Place.website, has_website)
    if has_opening_hours is True:
        query = query.filter(Place.opening_hours.isnot(None))
    elif has_opening_hours is False:
        query = query.filter(Place.opening_hours.is_(None))
    if route_eligible is not None:
        query = query.filter(Place.is_route_eligible.is_(route_eligible))
    if is_active is not None:
        query = query.filter(Place.is_active.is_(is_active))
    if searchable is not None:
        query = query.filter(Place.is_searchable.is_(searchable))
    if low_confidence:
        query = query.filter(Place.existence_confidence_level.in_(("low", "unknown")))
    if quality_tier:
        query = query.filter(Place.quality_tier == quality_tier)
    if source:
        query = query.filter(Place.source == source)
    if preset:
        query = apply_place_preset(query, preset)
    return query


def _presence_filter(query: Query, column, value: bool | None) -> Query:
    if value is True:
        return query.filter(column.isnot(None), column != "")
    if value is False:
        return query.filter(or_(column.is_(None), column == ""))
    return query


def _canonical_category_clause(values: tuple[str, ...]):
    return or_(Place.canonical_category.in_(values), Place.category.in_(values))


def _placeholder_clause():
    return or_(*tuple(Place.title.ilike(pattern) for pattern in PLACEHOLDER_SQL_PATTERNS))
