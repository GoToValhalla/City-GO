"""Фильтры и быстрые выборки списка мест в админке."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.destination import Destination, DestinationPlaceMembership
from models.place import Place
from services.admin_backlog_clauses import reason_clause
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

# Реальные инфраструктурные категории не являются мусором. Здесь остаются только
# неразобранные общие значения, требующие нормализации.
NON_SERVICE_ROUTE_CATEGORIES = {"unknown", "other", "useful"}
JUNK_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES | NON_SERVICE_ROUTE_CATEGORIES))
SERVICE_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES - NON_SERVICE_ROUTE_CATEGORIES))
MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
VERIFICATION_QUEUE_STATUSES = ("needs_recheck", "unverified")
MIN_DESCRIPTION_LENGTH = 40
GENERIC_DESCRIPTION_MARKERS = ("описание будет добавлено", "нет описания", "description pending", "todo", "вставьте описание")


def _search_terms(value: str, *, dialect: str = "postgresql") -> tuple[str, ...]:
    """PostgreSQL's ILIKE is already fully Unicode case-insensitive, so a single
    term is correct and avoids multiplying leading-wildcard scan cost 6x across
    3 columns. SQLite's LIKE/ILIKE only case-folds ASCII, so the test suite
    (and any SQLite deployment) still needs the case-variant fallback to match
    Cyrillic/mixed-case data regardless of search-term casing.
    """
    text = value.strip()
    if not text:
        return ()
    if dialect != "sqlite":
        return (f"%{text}%",)
    variants = (text, text.casefold(), text.lower(), text.capitalize(), text.title(), text.upper())
    return tuple(dict.fromkeys(f"%{item}%" for item in variants if item))


def apply_place_preset(query: Query, preset: str) -> Query:
    rules = {
        "no_photo": lambda q: q.filter(or_(Place.image_url.is_(None), Place.image_url == "")),
        "no_address": lambda q: q.filter(or_(Place.address.is_(None), Place.address == "")),
        "no_description": lambda q: q.filter(_description_missing_clause()),
        "no_contacts": lambda q: q.filter(or_(Place.phone.is_(None), Place.phone == ""), or_(Place.website.is_(None), Place.website == "")),
        "no_hours": lambda q: q.filter(Place.opening_hours.is_(None)),
        "low_confidence": lambda q: q.filter(Place.existence_confidence_level.in_(("low", "unknown"))),
        "needs_review": lambda q: q.filter(Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES)),
        "manual_review": lambda q: q.filter(Place.publication_status.in_(MANUAL_REVIEW_STATUSES)),
        "auto_backlog": lambda q: q.filter(Place.publication_status.in_(AUTO_BACKLOG_STATUSES)),
        "needs_verification": lambda q: q.filter(Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES)),
        "route_blockers": lambda q: q.filter(_route_blocker_clause()),
        "route_excluded": lambda q: q.filter(_published_catalog_clause(), _canonical_category_clause(SERVICE_CATEGORIES)),
        "not_in_routes": lambda q: q.filter(Place.is_published.is_(True), Place.is_route_eligible.is_not(True)),
        "route_unknown": lambda q: q.filter(_published_catalog_clause(), _unknown_category_clause()),
        "in_routes": lambda q: q.filter(Place.is_route_eligible.is_(True), Place.is_published.is_(True)),
        "published_not_route_eligible": lambda q: q.filter(_published_catalog_clause(), Place.is_route_eligible.is_(False)),
        "published_no_photo": lambda q: q.filter(_published_catalog_clause(), or_(Place.image_url.is_(None), Place.image_url == "")),
        "published_no_address": lambda q: q.filter(_published_catalog_clause(), or_(Place.address.is_(None), Place.address == "")),
        "published_no_description": lambda q: q.filter(_published_catalog_clause(), _description_missing_clause()),
        "published_low_confidence": lambda q: q.filter(_published_catalog_clause(), Place.existence_confidence_level.in_(("low", "unknown"))),
        "route_eligible_no_photo": lambda q: q.filter(Place.is_route_eligible.is_(True), or_(Place.image_url.is_(None), Place.image_url == "")),
        "route_eligible_no_address": lambda q: q.filter(Place.is_route_eligible.is_(True), or_(Place.address.is_(None), Place.address == "")),
        "generic_osm_placeholders": lambda q: q.filter(_placeholder_clause()),
        "junk_categories": lambda q: q.filter(_canonical_category_clause(JUNK_CATEGORIES)),
        "service_places": lambda q: q.filter(_published_catalog_clause(), _canonical_category_clause(SERVICE_CATEGORIES)),
        "problematic": lambda q: q.filter(or_(
            Place.image_url.is_(None),
            Place.address.is_(None),
            _description_missing_clause(),
            Place.existence_confidence_level.in_(("low", "unknown")),
            Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES),
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
    destination_slug: str | None = None,
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
    reason: str | None = None,
) -> Query:
    if city_slug:
        query = query.join(City).filter(City.slug == city_slug)
    if destination_slug:
        query = (
            query.join(DestinationPlaceMembership, DestinationPlaceMembership.place_id == Place.id)
            .join(Destination, Destination.id == DestinationPlaceMembership.destination_id)
            .filter(
                Destination.slug == destination_slug,
                DestinationPlaceMembership.is_hidden.is_(False),
                DestinationPlaceMembership.invalidated_at.is_(None),
            )
        )
    if publication_status:
        query = query.filter(Place.publication_status == publication_status)
    if verification_status:
        query = query.filter(Place.verification_status == verification_status)
    if category:
        query = query.filter(or_(Place.canonical_category == category, Place.category == category))
    if q:
        dialect = db.get_bind().dialect.name
        clauses = tuple(or_(Place.title.ilike(term), Place.slug.ilike(term), Place.address.ilike(term)) for term in _search_terms(q, dialect=dialect))
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
    if reason:
        clause = reason_clause(reason)
        if clause is not None:
            query = query.filter(clause)
    return query


def _presence_filter(query: Query, column, value: bool | None) -> Query:
    if value is True:
        return query.filter(column.isnot(None), column != "")
    if value is False:
        return query.filter(or_(column.is_(None), column == ""))
    return query


def _description_missing_clause():
    text = func.lower(func.trim(Place.short_description))
    return or_(
        Place.short_description.is_(None),
        Place.short_description == "",
        Place.short_description == Place.title,
        func.length(func.trim(Place.short_description)) < MIN_DESCRIPTION_LENGTH,
        *[text.contains(marker) for marker in GENERIC_DESCRIPTION_MARKERS],
    )


def _canonical_category_clause(values: tuple[str, ...]):
    return or_(Place.canonical_category.in_(values), Place.category.in_(values))


def _placeholder_clause():
    return or_(*tuple(Place.title.ilike(pattern) for pattern in PLACEHOLDER_SQL_PATTERNS))


def _published_catalog_clause():
    return Place.is_active.is_(True) & Place.is_published.is_(True) & Place.is_visible_in_catalog.is_(True) & or_(Place.status.is_(None), Place.status == "active")


def _unknown_category_clause():
    return or_(Place.canonical_category.is_(None), Place.canonical_category == "unknown", Place.category == "unknown")


def _route_blocker_clause():
    return _published_catalog_clause() & or_(
        Place.is_route_eligible.is_not(True),
        Place.lat.is_(None),
        Place.lng.is_(None),
        _canonical_category_clause(SERVICE_CATEGORIES),
        _unknown_category_clause(),
    )
