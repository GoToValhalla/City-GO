"""Deterministic place issue detection."""

from __future__ import annotations

from collections.abc import Iterable

from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.data_quality.constants import (
    ISSUE_LOW_CONFIDENCE,
    ISSUE_MISSING_ADDRESS,
    ISSUE_MISSING_PHOTO,
    ISSUE_REQUIRES_REVIEW,
    ISSUE_ROUTE_SUSPICIOUS,
    ISSUE_WEAK_DESCRIPTION,
    STOPLIST_CATEGORIES,
)
from services.data_quality.fingerprint import issue_fingerprint
from services.data_quality.types import IssueDraft


def detect_place_issues(
    place: Place,
    *,
    source_observations: Iterable[SourceObservation] = (),
    confidence_fields: Iterable[PlaceFieldConfidence] = (),
    review_items: Iterable[ReviewQueueItem] = (),
    confidence_threshold: float = 0.5,
) -> list[IssueDraft]:
    signals = [
        _missing_photo(place),
        _missing_address(place),
        _weak_description(place),
        _route_suspicious(place, source_observations),
        *_low_confidence(place, confidence_fields, confidence_threshold),
        *_requires_review(place, review_items),
    ]
    return [draft for draft in signals if draft is not None]


def _draft(place: Place, issue_type: str, severity: str, reason: str, evidence: dict[str, object]) -> IssueDraft:
    source = "deterministic"
    return IssueDraft(
        place_id=place.id,
        city_id=place.city_id,
        issue_type=issue_type,
        severity=severity,
        reason=reason,
        source=source,
        evidence=evidence,
        fingerprint=issue_fingerprint(
            place_id=place.id, city_id=place.city_id, issue_type=issue_type, reason=reason, source=source,
        ),
    )


def _is_public(place: Place) -> bool:
    return bool(place.is_published or place.is_visible_in_catalog or place.publication_status == "published")


def _missing_photo(place: Place) -> IssueDraft | None:
    has_photo = bool((place.image_url or "").strip()) or bool(getattr(place, "images", None) or [])
    if has_photo:
        return None
    severity = "high" if _is_public(place) else "warning"
    return _draft(place, ISSUE_MISSING_PHOTO, severity, "primary_photo_missing", {"image_url": place.image_url})


def _missing_address(place: Place) -> IssueDraft | None:
    if bool((place.address or "").strip()):
        return None
    severity = "high" if _is_public(place) or place.is_route_eligible else "warning"
    return _draft(place, ISSUE_MISSING_ADDRESS, severity, "address_missing", {"address": place.address})


def _weak_description(place: Place) -> IssueDraft | None:
    value = (place.short_description or "").strip()
    if len(value) >= 24 and value.lower() not in {"todo", "tbd", "описание"}:
        return None
    return _draft(place, ISSUE_WEAK_DESCRIPTION, "info", "description_empty_or_short", {"length": len(value)})


def _low_confidence(place: Place, rows: Iterable[PlaceFieldConfidence], threshold: float) -> list[IssueDraft]:
    return [
        _draft(place, ISSUE_LOW_CONFIDENCE, "warning", f"low_confidence:{row.field_name}", {
            "field": row.field_name, "confidence": row.confidence, "threshold": threshold, "source": row.source_type,
        })
        for row in rows
        if row.confidence < threshold
    ]


def _requires_review(place: Place, rows: Iterable[ReviewQueueItem]) -> list[IssueDraft]:
    return [
        _draft(place, ISSUE_REQUIRES_REVIEW, row.severity or "warning", f"review:{row.field_name}:{row.reason}", {
            "review_item_id": row.id, "field": row.field_name, "reason": row.reason,
        })
        for row in rows
        if row.status == "open"
    ]


def _route_suspicious(place: Place, rows: Iterable[SourceObservation]) -> IssueDraft | None:
    if not bool(place.is_route_eligible):
        return None
    matches = sorted(_category_signals(place, rows) & STOPLIST_CATEGORIES)
    if not matches:
        return None
    return _draft(place, ISSUE_ROUTE_SUSPICIOUS, "high", f"stoplist_category:{matches[0]}", {
        "matched_categories": matches, "place_category": place.category, "canonical_category": place.canonical_category,
    })


def _category_signals(place: Place, rows: Iterable[SourceObservation]) -> set[str]:
    direct = {place.category, place.canonical_category, getattr(place.category_ref, "code", None)}
    observed = {row.raw_category for row in rows}
    tagged = {_tag_value(row.raw_payload, key) for row in rows for key in ("amenity", "shop", "public_transport", "railway")}
    return {str(item).strip().lower() for item in direct | observed | tagged if item}


def _tag_value(payload: dict[str, object] | None, key: str) -> str | None:
    tags = payload.get("tags") if isinstance(payload, dict) else None
    value = tags.get(key) if isinstance(tags, dict) else None
    return str(value) if value else None
