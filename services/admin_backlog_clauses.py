"""Shared SQL clauses for admin backlog diagnostics."""

from __future__ import annotations

from sqlalchemy import and_, func, not_, or_

from models.place import Place
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

LOW_CONFIDENCE_LEVELS = ("low", "unknown")
VERIFICATION_QUEUE_STATUSES = ("needs_recheck", "unverified")
MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
MIN_DESCRIPTION_LENGTH = 40
DESCRIPTION_MARKERS = ("описание будет добавлено", "Описание будет добавлено", "нет описания", "Нет описания", "description pending", "todo", "вставьте описание", "Вставьте описание")
NON_SERVICE_ROUTE_CATEGORIES = {"unknown", "other", "useful"}
SERVICE_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES - NON_SERVICE_ROUTE_CATEGORIES))
MEDICAL_CATEGORIES = ("apteka", "clinic", "health", "healthcare", "hospital", "medical", "pharmacy")
BANK_CATEGORIES = ("atm", "bank")
TRANSPORT_CATEGORIES = ("bus_stop", "public_transport", "stop", "tram_stop", "transport", "transport_stop")
PARKING_CATEGORIES = ("fuel", "gas_station", "parking")
PLACEHOLDER_ADDRESS_MARKERS = ("адрес уточняется", "нет адреса", "unknown", "n/a")


def published_catalog_clause():
    return Place.is_active.is_(True) & Place.is_published.is_(True) & Place.is_visible_in_catalog.is_(True) & or_(Place.status.is_(None), Place.status == "active")


def missing_text(column):
    return or_(column.is_(None), func.length(func.trim(column)) == 0)


def category_clause(values: tuple[str, ...]):
    return or_(Place.canonical_category.in_(values), Place.category.in_(values))


def unknown_category_clause():
    return or_(Place.canonical_category.is_(None), Place.canonical_category == "unknown", Place.category == "unknown")


def service_category_clause():
    return category_clause(SERVICE_CATEGORIES)


def description_missing_clause():
    text = func.lower(func.trim(Place.short_description))
    return or_(Place.short_description.is_(None), func.length(func.trim(Place.short_description)) < MIN_DESCRIPTION_LENGTH, text == func.lower(func.trim(Place.title)), *[Place.short_description.ilike(f"%{marker}%") for marker in DESCRIPTION_MARKERS])


def content_gap_clause():
    published = published_catalog_clause()
    return published & or_(missing_text(Place.image_url), missing_text(Place.address), description_missing_clause())


def route_blocker_clause():
    published = published_catalog_clause()
    return published & or_(Place.is_route_eligible.is_not(True), Place.lat.is_(None), Place.lng.is_(None), unknown_category_clause(), service_category_clause())


def queue_clause(code: str):
    published = published_catalog_clause()
    mapping = {
        "route_blockers": route_blocker_clause(),
        "route_unknown": published & unknown_category_clause(),
        "route_excluded": published & service_category_clause(),
        "no_photo": published & missing_text(Place.image_url),
        "no_address": published & missing_text(Place.address),
        "no_description": published & description_missing_clause(),
        "low_confidence": published & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS),
        "auto_backlog": Place.publication_status.in_(AUTO_BACKLOG_STATUSES),
        "manual_review": Place.publication_status.in_(MANUAL_REVIEW_STATUSES),
        "needs_verification": Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES),
    }
    return mapping.get(code)


def reason_clause(code: str):
    published = published_catalog_clause()
    empty_category = or_(Place.canonical_category.is_(None), Place.canonical_category == "", Place.category.is_(None), Place.category == "")
    address_text = func.lower(func.trim(Place.address))
    description_text = func.lower(func.trim(Place.short_description))
    route_ready = published & Place.is_route_eligible.is_(True)
    mapping = {
        "manual_disabled": published & Place.is_route_eligible.is_(False),
        "missing_coordinates": published & or_(Place.lat.is_(None), Place.lng.is_(None)),
        "unknown_category": published & unknown_category_clause(),
        "service_category": published & service_category_clause(),
        "other_policy_blocker": published & Place.is_route_eligible.is_not(True) & not_(Place.is_route_eligible.is_(False)),
        "empty_category": published & empty_category,
        "unmapped_category": published & Place.canonical_category.is_(None) & Place.category.isnot(None) & (Place.category != ""),
        "placeholder_category": published & category_clause(("other", "useful")),
        "pharmacy_medical": published & category_clause(MEDICAL_CATEGORIES),
        "bank_atm": published & category_clause(BANK_CATEGORIES),
        "transport_bus_stop": published & category_clause(TRANSPORT_CATEGORIES),
        "parking_fuel": published & category_clause(PARKING_CATEGORIES),
        "other_service": published & service_category_clause() & not_(category_clause(MEDICAL_CATEGORIES + BANK_CATEGORIES + TRANSPORT_CATEGORIES + PARKING_CATEGORIES)),
        "published_without_any_photo": published & missing_text(Place.image_url),
        "route_ready_without_photo": route_ready & missing_text(Place.image_url),
        "catalog_without_photo": published & missing_text(Place.image_url),
        "address_null": published & Place.address.is_(None),
        "address_empty": published & (func.length(func.trim(Place.address)) == 0),
        "address_placeholder": published & or_(*[address_text.contains(marker) for marker in PLACEHOLDER_ADDRESS_MARKERS]),
        "coordinates_without_address": published & Place.lat.isnot(None) & Place.lng.isnot(None) & missing_text(Place.address),
        "description_null": published & Place.short_description.is_(None),
        "description_empty": published & (func.length(func.trim(Place.short_description)) == 0),
        "description_equals_title": published & (description_text == func.lower(func.trim(Place.title))),
        "description_too_short": published & Place.short_description.isnot(None) & (func.length(func.trim(Place.short_description)) > 0) & (func.length(func.trim(Place.short_description)) < MIN_DESCRIPTION_LENGTH),
        "placeholder_description": published & or_(*[Place.short_description.ilike(f"%{marker}%") for marker in DESCRIPTION_MARKERS]),
        "data_confidence_low": published & (Place.existence_confidence_level == "low"),
        "confidence_unknown": published & (Place.existence_confidence_level == "unknown"),
        "category_confidence_low": published & (Place.confidence_score < 3),
        "mixed_low_confidence": published & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS) & (Place.quality_score < 50),
        "explicit_manual_review": Place.publication_status.in_(("needs_manual_review", "deferred")),
        "legacy_needs_review": Place.publication_status == "needs_review",
        "publication_review_backlog": Place.publication_status.in_(MANUAL_REVIEW_STATUSES),
        "overlaps_with_auto_backlog": Place.publication_status.in_(MANUAL_REVIEW_STATUSES) & Place.publication_status.in_(AUTO_BACKLOG_STATUSES),
        "overlaps_with_verification": Place.publication_status.in_(MANUAL_REVIEW_STATUSES) & Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES),
        "overlaps_with_content_gaps": Place.publication_status.in_(MANUAL_REVIEW_STATUSES) & content_gap_clause(),
        "overlaps_with_low_confidence": Place.publication_status.in_(MANUAL_REVIEW_STATUSES) & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS),
        "verification_overlaps_with_manual_review": Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES) & Place.publication_status.in_(MANUAL_REVIEW_STATUSES),
        "verification_overlaps_with_low_confidence": Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES) & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS),
        "verification_overlaps_with_content_gaps": Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES) & content_gap_clause(),
        "auto_draft": Place.publication_status == "draft",
        "auto_backlog_status": Place.publication_status == "auto_backlog",
        "auto_low_confidence_status": Place.publication_status == "low_confidence",
        "needs_recheck": Place.verification_status == "needs_recheck",
        "unverified": Place.verification_status == "unverified",
        "route_relevant_verification": published & Place.is_route_eligible.is_(True) & Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES),
    }
    return mapping.get(code)
