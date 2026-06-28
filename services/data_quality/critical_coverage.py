"""Category-aware critical data coverage triage for admin quality screens.

This module is intentionally read-only. It defines the contract that can later be
materialized into Place.quality_bucket without changing the admin API shape.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.place_photo_candidate import PlacePhotoCandidate
from models.place_schedule import PlaceSchedule
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.data_quality.constants import STOPLIST_CATEGORIES


class FieldRequirement(str, Enum):
    ROUTE_CRITICAL = "route_critical"
    CARD_REQUIRED = "card_required"
    AUTO_ENRICHABLE = "auto_enrichable"
    MANUAL_ONLY = "manual_only"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"


class TriageBucket(str, Enum):
    ROUTE_BLOCKER = "route_blocker"
    CARD_BLOCKER = "card_blocker"
    AUTO_ENRICHMENT_CANDIDATE = "auto_enrichment_candidate"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    OPTIONAL_GAP = "optional_gap"
    NOT_APPLICABLE = "not_applicable"
    ROUTE_EXCLUDED = "route_excluded"
    ROUTE_READY = "route_ready"
    CARD_READY = "card_ready"


@dataclass(frozen=True)
class CategoryProfile:
    category_group: str
    is_tourist_eligible: bool
    fields: dict[str, FieldRequirement]


@dataclass(frozen=True)
class FieldIssue:
    field_name: str
    bucket: TriageBucket
    reason: str
    auto_action: str | None = None


@dataclass
class PlaceTriageContext:
    has_normalized_schedule: bool = False
    has_pending_photo_candidates: bool = False
    has_source_observations: bool = False
    confidence_by_field: dict[str, PlaceFieldConfidence] = field(default_factory=dict)
    open_review_items: list[ReviewQueueItem] = field(default_factory=list)


@dataclass
class PlaceTriageResult:
    place_id: int
    place_name: str
    canonical_category: str | None
    profile_key: str
    is_tourist_eligible: bool
    route_status: TriageBucket
    card_status: TriageBucket
    route_blockers: list[FieldIssue] = field(default_factory=list)
    card_blockers: list[FieldIssue] = field(default_factory=list)
    auto_enrichment_candidates: list[FieldIssue] = field(default_factory=list)
    manual_review_items: list[FieldIssue] = field(default_factory=list)
    optional_gaps: list[FieldIssue] = field(default_factory=list)
    has_pending_photo_candidates: bool = False
    has_open_review_queue_items: bool = False
    has_opening_hours: bool = False
    confidence_flags: list[str] = field(default_factory=list)


CATEGORY_PROFILES: dict[str, CategoryProfile] = {
    "landmark": CategoryProfile(
        category_group="landmark",
        is_tourist_eligible=True,
        fields={
            "name": FieldRequirement.ROUTE_CRITICAL,
            "lat": FieldRequirement.ROUTE_CRITICAL,
            "lng": FieldRequirement.ROUTE_CRITICAL,
            "canonical_category": FieldRequirement.ROUTE_CRITICAL,
            "short_description": FieldRequirement.CARD_REQUIRED,
            "image_url": FieldRequirement.CARD_REQUIRED,
            "address": FieldRequirement.OPTIONAL,
            "opening_hours": FieldRequirement.NOT_APPLICABLE,
        },
    ),
    "museum": CategoryProfile(
        category_group="museum",
        is_tourist_eligible=True,
        fields={
            "name": FieldRequirement.ROUTE_CRITICAL,
            "lat": FieldRequirement.ROUTE_CRITICAL,
            "lng": FieldRequirement.ROUTE_CRITICAL,
            "canonical_category": FieldRequirement.ROUTE_CRITICAL,
            "opening_hours": FieldRequirement.ROUTE_CRITICAL,
            "short_description": FieldRequirement.CARD_REQUIRED,
            "image_url": FieldRequirement.CARD_REQUIRED,
            "address": FieldRequirement.CARD_REQUIRED,
            "website": FieldRequirement.OPTIONAL,
        },
    ),
    "park": CategoryProfile(
        category_group="park",
        is_tourist_eligible=True,
        fields={
            "name": FieldRequirement.ROUTE_CRITICAL,
            "lat": FieldRequirement.ROUTE_CRITICAL,
            "lng": FieldRequirement.ROUTE_CRITICAL,
            "canonical_category": FieldRequirement.ROUTE_CRITICAL,
            "short_description": FieldRequirement.CARD_REQUIRED,
            "image_url": FieldRequirement.CARD_REQUIRED,
            "address": FieldRequirement.OPTIONAL,
            "opening_hours": FieldRequirement.OPTIONAL,
        },
    ),
    "restaurant": CategoryProfile(
        category_group="restaurant",
        is_tourist_eligible=True,
        fields={
            "name": FieldRequirement.ROUTE_CRITICAL,
            "lat": FieldRequirement.ROUTE_CRITICAL,
            "lng": FieldRequirement.ROUTE_CRITICAL,
            "canonical_category": FieldRequirement.ROUTE_CRITICAL,
            "opening_hours": FieldRequirement.ROUTE_CRITICAL,
            "address": FieldRequirement.CARD_REQUIRED,
            "image_url": FieldRequirement.CARD_REQUIRED,
            "short_description": FieldRequirement.AUTO_ENRICHABLE,
            "price_level": FieldRequirement.OPTIONAL,
        },
    ),
    "service": CategoryProfile(category_group="service", is_tourist_eligible=False, fields={}),
}

CANONICAL_TO_PROFILE: dict[str, str] = {
    "landmark": "landmark",
    "monument": "landmark",
    "memorial": "landmark",
    "viewpoint": "landmark",
    "square": "landmark",
    "attraction": "landmark",
    "church": "landmark",
    "cathedral": "landmark",
    "museum": "museum",
    "gallery": "museum",
    "paid_attraction": "museum",
    "theatre": "museum",
    "theater": "museum",
    "cinema": "museum",
    "park": "park",
    "promenade": "park",
    "beach": "park",
    "garden": "park",
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "bar": "restaurant",
    "food": "restaurant",
    "pharmacy": "service",
    "bank": "service",
    "atm": "service",
    "bus_stop": "service",
    "transit_stop": "service",
    "railway_station": "service",
    "parking": "service",
    "toilets": "service",
    "toilet": "service",
    "utility": "service",
    "industrial": "service",
    "government": "service",
    "police": "service",
    "hospital": "service",
    "clinic": "service",
    "post_office": "service",
    "service": "service",
}

AUTO_ACTION_MAP = {
    "address": "run_address_geocoding",
    "short_description": "run_ai_description_candidate",
    "opening_hours": "run_hours_enrichment",
}

PHOTO_CANDIDATE_OPEN_STATUSES = {"candidate", "pending", "needs_review", "open"}
CRITICAL_CONFIDENCE_FIELDS = {"name", "canonical_category", "lat", "lng", "opening_hours"}


def build_city_critical_coverage(
    db: Session,
    *,
    city_slug: str,
    category: str | None = None,
) -> dict[str, Any] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    query = _city_places_query(db, city.id, category)
    summary = compute_city_critical_coverage(db, query)
    return {
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "category": category,
        **summary,
    }


def list_city_critical_coverage_places(
    db: Session,
    *,
    city_slug: str,
    category: str | None = None,
    bucket: str | None = None,
    reason: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    places = _city_places_query(db, city.id, category).all()
    contexts = _load_contexts(db, [place.id for place in places])
    rows = [
        (place, triage_place(place, contexts.get(place.id, PlaceTriageContext())))
        for place in places
    ]
    filtered = [
        (place, result)
        for place, result in rows
        if _matches_bucket(result, bucket) and _matches_reason(result, reason)
    ]
    filtered.sort(key=lambda item: _sort_key(item[1]))
    paged = filtered[offset: offset + limit]
    return {
        "city_id": city.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "bucket": bucket,
        "reason": reason,
        "category": category,
        "items": [_place_result_payload(place, result) for place, result in paged],
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
    }


def compute_city_critical_coverage(db: Session, places_query: Query) -> dict[str, Any]:
    places = places_query.all()
    contexts = _load_contexts(db, [place.id for place in places])
    results = [triage_place(place, contexts.get(place.id, PlaceTriageContext())) for place in places]
    return aggregate_triage_results(results, places)


def triage_place(place: Place, context: PlaceTriageContext | None = None) -> PlaceTriageResult:
    ctx = context or PlaceTriageContext()
    category = _category_key(place)
    profile_key = _profile_key(category)
    profile = CATEGORY_PROFILES.get(profile_key)
    title = _text(getattr(place, "title", None))

    if _is_non_tourist(place, category, profile):
        return PlaceTriageResult(
            place_id=place.id,
            place_name=title,
            canonical_category=category,
            profile_key=profile_key,
            is_tourist_eligible=False,
            route_status=TriageBucket.ROUTE_EXCLUDED,
            card_status=TriageBucket.NOT_APPLICABLE,
        )

    if profile is None:
        profile = CATEGORY_PROFILES["landmark"]

    route_blockers: list[FieldIssue] = []
    card_blockers: list[FieldIssue] = []
    auto_candidates: list[FieldIssue] = []
    manual_items: list[FieldIssue] = []
    optional_gaps: list[FieldIssue] = []
    confidence_flags: list[str] = []

    if not bool(place.is_route_eligible):
        route_blockers.append(_issue("is_route_eligible", TriageBucket.ROUTE_BLOCKER, "route_ineligible"))
    if not category:
        route_blockers.append(_issue("canonical_category", TriageBucket.ROUTE_BLOCKER, "missing_canonical_category"))
    elif profile_key == "unknown":
        route_blockers.append(_issue("canonical_category", TriageBucket.ROUTE_BLOCKER, "unknown_category"))

    for field_name, requirement in profile.fields.items():
        missing = _field_missing(place, field_name, ctx)
        fc = ctx.confidence_by_field.get(field_name)
        conflicted = bool(fc and fc.conflict_status == "conflict" and not fc.is_manual_verified)
        low_confidence = bool(fc and fc.field_name in CRITICAL_CONFIDENCE_FIELDS and fc.confidence < 0.5)

        if conflicted and requirement in {FieldRequirement.ROUTE_CRITICAL, FieldRequirement.CARD_REQUIRED}:
            reason = "source_conflict_unresolved"
            manual_items.append(_issue(field_name, TriageBucket.MANUAL_REVIEW_REQUIRED, reason))
            confidence_flags.append(f"conflict:{field_name}")
            if requirement == FieldRequirement.ROUTE_CRITICAL:
                route_blockers.append(_issue(field_name, TriageBucket.ROUTE_BLOCKER, reason))
            continue

        if low_confidence and requirement == FieldRequirement.ROUTE_CRITICAL:
            reason = "low_confidence_critical_field"
            manual_items.append(_issue(field_name, TriageBucket.MANUAL_REVIEW_REQUIRED, reason))
            route_blockers.append(_issue(field_name, TriageBucket.ROUTE_BLOCKER, reason))
            confidence_flags.append(f"low_confidence:{field_name}")
            continue

        if not missing:
            continue
        if requirement == FieldRequirement.ROUTE_CRITICAL:
            route_blockers.append(_issue(field_name, TriageBucket.ROUTE_BLOCKER, f"missing_{field_name}"))
            _append_auto_candidate(auto_candidates, field_name, ctx)
        elif requirement == FieldRequirement.CARD_REQUIRED:
            card_blockers.append(_issue(field_name, TriageBucket.CARD_BLOCKER, f"missing_{field_name}"))
            _append_auto_candidate(auto_candidates, field_name, ctx)
        elif requirement == FieldRequirement.AUTO_ENRICHABLE:
            _append_auto_candidate(auto_candidates, field_name, ctx, fallback=True)
        elif requirement == FieldRequirement.OPTIONAL:
            optional_gaps.append(_issue(field_name, TriageBucket.OPTIONAL_GAP, f"missing_{field_name}"))

    for review_item in ctx.open_review_items:
        manual_items.append(_issue(
            review_item.field_name,
            TriageBucket.MANUAL_REVIEW_REQUIRED,
            f"review:{review_item.reason}",
        ))

    if not _has_photo(place) and ctx.has_pending_photo_candidates:
        manual_items.append(_issue("image_url", TriageBucket.MANUAL_REVIEW_REQUIRED, "pending_photo_candidates_need_review"))

    route_status = TriageBucket.ROUTE_BLOCKER if route_blockers else TriageBucket.ROUTE_READY
    card_status = TriageBucket.CARD_BLOCKER if card_blockers else TriageBucket.CARD_READY
    return PlaceTriageResult(
        place_id=place.id,
        place_name=title,
        canonical_category=category,
        profile_key=profile_key,
        is_tourist_eligible=True,
        route_status=route_status,
        card_status=card_status,
        route_blockers=_dedupe_issues(route_blockers),
        card_blockers=_dedupe_issues(card_blockers),
        auto_enrichment_candidates=_dedupe_issues(auto_candidates),
        manual_review_items=_dedupe_issues(manual_items),
        optional_gaps=_dedupe_issues(optional_gaps),
        has_pending_photo_candidates=ctx.has_pending_photo_candidates,
        has_open_review_queue_items=bool(ctx.open_review_items),
        has_opening_hours=_has_hours(place, ctx),
        confidence_flags=sorted(set(confidence_flags)),
    )


def aggregate_triage_results(results: list[PlaceTriageResult], places: list[Place]) -> dict[str, Any]:
    place_by_id = {place.id: place for place in places}
    tourist = [row for row in results if row.is_tourist_eligible]
    not_applicable = len(results) - len(tourist)
    route_ready = sum(1 for row in tourist if row.route_status == TriageBucket.ROUTE_READY)
    route_blocked = sum(1 for row in tourist if row.route_status == TriageBucket.ROUTE_BLOCKER)
    card_ready = sum(1 for row in tourist if row.card_status == TriageBucket.CARD_READY)
    card_blocked = sum(1 for row in tourist if row.card_status == TriageBucket.CARD_BLOCKER)
    auto_places = sum(1 for row in tourist if row.auto_enrichment_candidates)
    manual_places = sum(1 for row in tourist if row.manual_review_items)
    optional_places = sum(1 for row in tourist if row.optional_gaps and not row.route_blockers and not row.card_blockers)

    route_breakdown = _issue_counter(tourist, "route_blockers")
    card_breakdown = _issue_counter(tourist, "card_blockers")
    auto_breakdown = _auto_counter(tourist)
    manual_breakdown = _manual_counter(tourist)
    coverage = _coverage(tourist, place_by_id)
    route_ready_pct = round((route_ready / len(tourist)) * 100, 1) if tourist else 100.0
    min_route_ready = 70.0

    return {
        "places_total": len(places),
        "tourist_places": {
            "total": len(tourist),
            "route_ready": route_ready,
            "route_blocked": route_blocked,
            "card_ready": card_ready,
            "card_blocked": card_blocked,
            "excluded_non_tourist": not_applicable,
        },
        "route_candidate_total": len(tourist),
        "route_ready_total": route_ready,
        "route_blockers_total": route_blocked,
        "card_ready_total": card_ready,
        "card_blockers_total": card_blocked,
        "auto_enrichment_total": auto_places,
        "manual_review_total": manual_places,
        "optional_gaps_total": optional_places,
        "not_applicable_total": not_applicable,
        "route_blockers_breakdown": dict(route_breakdown),
        "card_blockers_breakdown": dict(card_breakdown),
        "auto_enrichment_queue": {
            "total": auto_places,
            "address_geocoding": auto_breakdown["address_geocoding"],
            "description_generation": auto_breakdown["description_generation"],
            "hours_enrichment": auto_breakdown["hours_enrichment"],
        },
        "manual_review_queue": {
            "total": manual_places,
            "pending_photo_review": manual_breakdown["pending_photo_review"],
            "source_conflicts": manual_breakdown["source_conflicts"],
            "low_confidence_critical": manual_breakdown["low_confidence_critical"],
            "review_queue_open": manual_breakdown["review_queue_open"],
        },
        "coverage": coverage,
        "next_actions": _next_actions(auto_places, auto_breakdown, manual_places, manual_breakdown, route_blocked),
        "city_readiness": {
            "route_ready_pct": route_ready_pct,
            "min_route_ready_for_launch": min_route_ready,
            "is_launch_ready": route_ready_pct >= min_route_ready and route_blocked == 0,
            "blocking_reason": None if route_ready_pct >= min_route_ready and route_blocked == 0 else "route_ready_pct below threshold or route blockers exist",
        },
    }


def _city_places_query(db: Session, city_id: int, category: str | None = None) -> Query:
    query = db.query(Place).filter(Place.city_id == city_id)
    if category:
        query = query.filter(Place.category == category)
    return query


def _load_contexts(db: Session, place_ids: list[int]) -> dict[int, PlaceTriageContext]:
    contexts = {place_id: PlaceTriageContext() for place_id in place_ids}
    if not place_ids:
        return contexts

    for place_id, in db.query(PlaceSchedule.place_id).filter(PlaceSchedule.place_id.in_(place_ids)).distinct().all():
        contexts[place_id].has_normalized_schedule = True

    for place_id, in db.query(PlacePhotoCandidate.place_id).filter(
        PlacePhotoCandidate.place_id.in_(place_ids),
        PlacePhotoCandidate.status.in_(PHOTO_CANDIDATE_OPEN_STATUSES),
    ).distinct().all():
        contexts[place_id].has_pending_photo_candidates = True

    for place_id, in db.query(SourceObservation.canonical_place_id).filter(
        SourceObservation.canonical_place_id.in_(place_ids),
    ).distinct().all():
        if place_id is not None:
            contexts[place_id].has_source_observations = True

    for row in db.query(PlaceFieldConfidence).filter(PlaceFieldConfidence.place_id.in_(place_ids)).all():
        contexts[row.place_id].confidence_by_field[row.field_name] = row

    for row in db.query(ReviewQueueItem).filter(
        ReviewQueueItem.place_id.in_(place_ids),
        ReviewQueueItem.status == "open",
    ).all():
        contexts[row.place_id].open_review_items.append(row)

    return contexts


def _matches_bucket(result: PlaceTriageResult, bucket: str | None) -> bool:
    if not bucket:
        return True
    normalized = bucket.strip().lower()
    return {
        "route_blocker": result.route_status == TriageBucket.ROUTE_BLOCKER,
        "route_ready": result.route_status == TriageBucket.ROUTE_READY,
        "card_blocker": result.card_status == TriageBucket.CARD_BLOCKER,
        "card_ready": result.card_status == TriageBucket.CARD_READY,
        "auto_enrichment_candidate": bool(result.auto_enrichment_candidates),
        "manual_review": bool(result.manual_review_items),
        "manual_review_required": bool(result.manual_review_items),
        "optional_gap": bool(result.optional_gaps),
        "not_applicable": not result.is_tourist_eligible,
        "route_excluded": result.route_status == TriageBucket.ROUTE_EXCLUDED,
    }.get(normalized, True)


def _matches_reason(result: PlaceTriageResult, reason: str | None) -> bool:
    if not reason:
        return True
    expected = reason.strip().lower()
    return any(issue.reason.lower() == expected for issue in _all_issues(result))


def _all_issues(result: PlaceTriageResult) -> list[FieldIssue]:
    return [
        *result.route_blockers,
        *result.card_blockers,
        *result.auto_enrichment_candidates,
        *result.manual_review_items,
        *result.optional_gaps,
    ]


def _sort_key(result: PlaceTriageResult) -> tuple[int, str, int]:
    priority = 0
    if result.route_status == TriageBucket.ROUTE_BLOCKER:
        priority = 1
    elif result.card_status == TriageBucket.CARD_BLOCKER:
        priority = 2
    elif result.manual_review_items:
        priority = 3
    elif result.auto_enrichment_candidates:
        priority = 4
    elif not result.is_tourist_eligible:
        priority = 9
    return (priority, result.place_name.lower(), result.place_id)


def _place_result_payload(place: Place, result: PlaceTriageResult) -> dict[str, Any]:
    return {
        "place": {
            "id": place.id,
            "slug": place.slug,
            "title": place.title,
            "category": place.category,
            "canonical_category": place.canonical_category,
            "address": place.address,
            "image_url": place.image_url,
            "is_route_eligible": place.is_route_eligible,
            "publication_status": place.publication_status,
            "has_photo": _has_photo(place),
            "has_address": not _field_missing(place, "address", PlaceTriageContext()),
            "has_opening_hours": result.has_opening_hours,
            "has_description": not _field_missing(place, "short_description", PlaceTriageContext()),
        },
        "profile_key": result.profile_key,
        "is_tourist_eligible": result.is_tourist_eligible,
        "route_status": result.route_status.value,
        "card_status": result.card_status.value,
        "route_blockers": [_issue_payload(item) for item in result.route_blockers],
        "card_blockers": [_issue_payload(item) for item in result.card_blockers],
        "auto_enrichment_candidates": [_issue_payload(item) for item in result.auto_enrichment_candidates],
        "manual_review_items": [_issue_payload(item) for item in result.manual_review_items],
        "optional_gaps": [_issue_payload(item) for item in result.optional_gaps],
        "confidence_flags": result.confidence_flags,
    }


def _issue_payload(item: FieldIssue) -> dict[str, Any]:
    return {
        "field_name": item.field_name,
        "bucket": item.bucket.value,
        "reason": item.reason,
        "auto_action": item.auto_action,
    }


def _category_key(place: Place) -> str | None:
    for value in (place.canonical_category, place.category, getattr(place.category_ref, "code", None)):
        normalized = _text(value).lower()
        if normalized:
            return normalized
    return None


def _profile_key(category: str | None) -> str:
    if not category:
        return "unknown"
    if category in STOPLIST_CATEGORIES:
        return "service"
    return CANONICAL_TO_PROFILE.get(category, "unknown")


def _is_non_tourist(place: Place, category: str | None, profile: CategoryProfile | None) -> bool:
    if bool(place.is_spam_poi):
        return True
    if place.lifecycle_status in {"archived", "deleted", "spam"}:
        return True
    if place.publication_status in {"archived", "duplicate_hidden", "rejected"}:
        return True
    if category in STOPLIST_CATEGORIES:
        return True
    return bool(profile and not profile.is_tourist_eligible)


def _field_missing(place: Place, field_name: str, context: PlaceTriageContext) -> bool:
    if field_name == "name":
        return not _text(getattr(place, "title", None))
    if field_name == "lat":
        return getattr(place, "lat", None) is None
    if field_name == "lng":
        return getattr(place, "lng", None) is None
    if field_name == "canonical_category":
        return not _category_key(place)
    if field_name == "image_url":
        return not _has_photo(place)
    if field_name == "opening_hours":
        return not _has_hours(place, context)
    value = getattr(place, field_name, None)
    if isinstance(value, str):
        return not value.strip()
    return value is None


def _has_photo(place: Place) -> bool:
    return bool(_text(getattr(place, "image_url", None)))


def _has_hours(place: Place, context: PlaceTriageContext) -> bool:
    return bool(getattr(place, "opening_hours", None)) or context.has_normalized_schedule


def _append_auto_candidate(
    target: list[FieldIssue],
    field_name: str,
    context: PlaceTriageContext,
    *,
    fallback: bool = False,
) -> None:
    action = AUTO_ACTION_MAP.get(field_name)
    if not action:
        return
    fc = context.confidence_by_field.get(field_name)
    has_confident_candidate = bool(fc and fc.confidence >= 0.8 and fc.raw_value)
    if context.has_source_observations or has_confident_candidate or fallback:
        target.append(_issue(field_name, TriageBucket.AUTO_ENRICHMENT_CANDIDATE, f"missing_{field_name}", action))


def _issue(field_name: str, bucket: TriageBucket, reason: str, auto_action: str | None = None) -> FieldIssue:
    return FieldIssue(field_name=field_name, bucket=bucket, reason=reason, auto_action=auto_action)


def _dedupe_issues(items: list[FieldIssue]) -> list[FieldIssue]:
    seen: set[tuple[str, str, str]] = set()
    result: list[FieldIssue] = []
    for item in items:
        key = (item.field_name, item.bucket.value, item.reason)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _issue_counter(rows: list[PlaceTriageResult], attr: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for issue in getattr(row, attr):
            counter[issue.reason] += 1
    return counter


def _auto_counter(rows: list[PlaceTriageResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    action_to_key = {
        "run_address_geocoding": "address_geocoding",
        "run_ai_description_candidate": "description_generation",
        "run_hours_enrichment": "hours_enrichment",
    }
    for row in rows:
        seen_for_place: set[str] = set()
        for issue in row.auto_enrichment_candidates:
            key = action_to_key.get(issue.auto_action or "")
            if key and key not in seen_for_place:
                counter[key] += 1
                seen_for_place.add(key)
    return counter


def _manual_counter(rows: list[PlaceTriageResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        reasons = {item.reason for item in row.manual_review_items}
        if "pending_photo_candidates_need_review" in reasons:
            counter["pending_photo_review"] += 1
        if any(reason == "source_conflict_unresolved" for reason in reasons):
            counter["source_conflicts"] += 1
        if any(reason == "low_confidence_critical_field" for reason in reasons):
            counter["low_confidence_critical"] += 1
        if any(reason.startswith("review:") for reason in reasons):
            counter["review_queue_open"] += 1
    return counter


def _coverage(rows: list[PlaceTriageResult], place_by_id: dict[int, Place]) -> dict[str, dict[str, float | int]]:
    tourist_places = [place_by_id[row.place_id] for row in rows]
    hours_rows = [row for row in rows if _hours_applicable(row.profile_key)]
    contextless = PlaceTriageContext()
    return {
        "has_approved_photo": _metric(sum(1 for place in tourist_places if _has_photo(place)), len(tourist_places)),
        "has_address": _metric(sum(1 for place in tourist_places if not _field_missing(place, "address", contextless)), len(tourist_places)),
        "has_description": _metric(
            sum(1 for place in tourist_places if not _field_missing(place, "short_description", contextless)),
            len(tourist_places),
        ),
        "has_opening_hours": _metric(sum(1 for row in hours_rows if row.has_opening_hours), len(hours_rows)),
    }


def _hours_applicable(profile_key: str) -> bool:
    requirement = CATEGORY_PROFILES.get(profile_key, CATEGORY_PROFILES["landmark"]).fields.get("opening_hours")
    return requirement not in {None, FieldRequirement.NOT_APPLICABLE}


def _metric(count: int, total: int) -> dict[str, float | int]:
    return {"count": count, "total": total, "pct": round((count / total) * 100, 1) if total else 100.0}


def _next_actions(
    auto_places: int,
    auto_breakdown: Counter[str],
    manual_places: int,
    manual_breakdown: Counter[str],
    route_blocked: int,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if route_blocked:
        actions.append({
            "type": "resolve_route_blockers",
            "label": "Разобрать блокеры маршрутов",
            "endpoint": "/admin/data-quality/issues",
            "filters": {"bucket": "route_blocker"},
            "affects_places": route_blocked,
            "expected_route_ready_gain": route_blocked,
        })
    if auto_places:
        actions.append({
            "type": "run_auto_enrichment",
            "label": "Запустить автообогащение адресов, описаний и часов",
            "endpoint": "/admin/place-enrichment/pipeline/{city_slug}/run",
            "params": {"tasks": [key for key, value in auto_breakdown.items() if value > 0]},
            "affects_places": auto_places,
            "expected_card_ready_gain": auto_places,
        })
    if manual_breakdown["pending_photo_review"]:
        actions.append({
            "type": "review_photo_candidates",
            "label": "Проверить фото-кандидаты",
            "endpoint": "/admin/place-enrichment/photo-candidates",
            "filters": {"status": "candidate"},
            "affects_places": manual_breakdown["pending_photo_review"],
            "expected_card_ready_gain": manual_breakdown["pending_photo_review"],
        })
    if manual_places:
        actions.append({
            "type": "open_manual_review_queue",
            "label": "Открыть ручную проверку конфликтов",
            "endpoint": "/admin/place-enrichment/review-queue",
            "filters": {"status": "open"},
            "affects_places": manual_places,
        })
    return actions


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""