from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import Any

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_change_review import PlaceChangeReview
from models.place_publication_decision import PlacePublicationDecision
from models.place_snapshot import PlaceSnapshot
from models.review_queue_item import ReviewQueueItem
from services.place_public_visibility import is_public_hidden_category
from services.place_quality_signals import is_placeholder_title
from services.publication_state_writer import (
    InvalidPublicationTransition,
    PUBLISHED_STATUS,
    REASON_PUBLISHED,
    transition_place_publication,
)

MODE_SHADOW = "shadow"
MODE_APPLY = "apply"

DECISION_AUTO_PUBLISH = "auto_publish"
DECISION_SHADOW_AUTO_PUBLISH = "shadow_auto_publish"
DECISION_REVIEW = "send_to_review"
DECISION_HIDDEN = "hidden"
DECISION_KEEP_PUBLISHED = "keep_published"

REASON_NEW_PLACE = "NEW_PLACE"
REASON_LOW_TRUST = "LOW_TRUST_SCORE"
REASON_HARD_GATE_FAILED = "HARD_GATE_FAILED"
REASON_DUPLICATE = "DUPLICATE_SUSPICION"
REASON_SUSPICIOUS = "SUSPICIOUS_CONTENT"
REASON_CRITICAL_FIELD_CHANGED = "CRITICAL_FIELD_CHANGED"
REASON_NAME_CHANGE = "NAME_CHANGE"
REASON_CATEGORY_CHANGE = "CATEGORY_CHANGE"
REASON_LOCATION_CHANGE = "LOCATION_CHANGE"
REASON_ADDRESS_CHANGE = "ADDRESS_CHANGE"
REASON_CLOSURE = "CLOSURE"

CRITICAL_FIELDS = {"title", "name", "category", "canonical_category", "category_id", "lat", "lng", "address", "lifecycle_status"}
AUTO_ACCEPT_FIELDS = {
    "image_url",
    "website",
    "phone",
    "opening_hours",
    "short_description",
    "atmosphere",
    "inside",
    "best_for",
    "quality_score",
    "photo_score",
    "description_score",
    "confidence_score",
    "freshness_score",
}


def _apply_auto_accept_field(place: Place, field_name: str, new_value: Any) -> None:
    """Assign one of AUTO_ACCEPT_FIELDS via literal attributes (no controlled fields)."""
    if field_name == "image_url":
        place.image_url = new_value
    elif field_name == "website":
        place.website = new_value
    elif field_name == "phone":
        place.phone = new_value
    elif field_name == "opening_hours":
        place.opening_hours = new_value
    elif field_name == "short_description":
        place.short_description = new_value
    elif field_name == "atmosphere":
        place.atmosphere = new_value
    elif field_name == "inside":
        place.inside = new_value
    elif field_name == "best_for":
        place.best_for = new_value
    elif field_name == "quality_score":
        place.quality_score = new_value
    elif field_name == "photo_score":
        place.photo_score = new_value
    elif field_name == "description_score":
        place.description_score = new_value
    elif field_name == "confidence_score":
        place.confidence_score = new_value
    elif field_name == "freshness_score":
        place.freshness_score = new_value


@dataclass(frozen=True)
class PublicationPolicyConfig:
    mode: str = MODE_SHADOW
    auto_publish_enabled: bool = False
    auto_publish_threshold: float = 90.0
    review_threshold: float = 60.0
    location_change_threshold_meters: float = 50.0


@dataclass(frozen=True)
class PublicationDecision:
    decision: str
    trust_score: float
    failed_gates: list[str]
    review_reasons: list[str]
    should_publish: bool = False


def evaluate_new_place(place: Place, *, city: City | None = None, config: PublicationPolicyConfig | None = None) -> PublicationDecision:
    config = config or PublicationPolicyConfig()
    city = city or place.city
    failed_gates = run_hard_gates(place, city=city)
    trust_score = calculate_trust_score(place)

    if failed_gates:
        return PublicationDecision(
            decision=DECISION_REVIEW if trust_score >= config.review_threshold else DECISION_HIDDEN,
            trust_score=trust_score,
            failed_gates=failed_gates,
            review_reasons=[REASON_HARD_GATE_FAILED],
        )

    if trust_score >= config.auto_publish_threshold:
        if config.mode == MODE_APPLY and config.auto_publish_enabled:
            return PublicationDecision(
                decision=DECISION_AUTO_PUBLISH,
                trust_score=trust_score,
                failed_gates=[],
                review_reasons=[],
                should_publish=True,
            )
        return PublicationDecision(
            decision=DECISION_SHADOW_AUTO_PUBLISH,
            trust_score=trust_score,
            failed_gates=[],
            review_reasons=[REASON_NEW_PLACE],
        )

    return PublicationDecision(
        decision=DECISION_REVIEW if trust_score >= config.review_threshold else DECISION_HIDDEN,
        trust_score=trust_score,
        failed_gates=[],
        review_reasons=[REASON_LOW_TRUST],
    )


def run_hard_gates(place: Place, *, city: City | None = None) -> list[str]:
    city = city or place.city
    failed: list[str] = []

    if city is None or not city.is_active or city.launch_status != "published":
        failed.append("city_not_published")

    if not place.title or len(place.title.strip()) < 3:
        failed.append("missing_name")
    elif is_placeholder_title(place.title):
        failed.append("generic_name_requires_review")

    if place.lat is None or place.lng is None or not (-90 <= place.lat <= 90) or not (-180 <= place.lng <= 180):
        failed.append("invalid_coordinates")
    elif city is not None and not _inside_city_bbox(place, city):
        failed.append("outside_city_bbox")

    category = place.canonical_category or place.category
    if not place.category_id and not category:
        failed.append("missing_category")
    elif is_public_hidden_category(category):
        failed.append("utility_category")

    if place.is_spam_poi:
        failed.append("spam_suspected")

    if place.is_duplicate_suspected:
        failed.append("duplicate_suspected")

    if place.lifecycle_status in {"closed", "permanently_closed", "archived"} or place.status in {"closed", "archived"}:
        failed.append("closed_place")

    return failed


def unsafe_manual_publish_gates(place: Place) -> list[str]:
    """Server-side safety gate for the manual "Опубликовать" admin action.

    run_hard_gates() covers structural data problems (name/coords/category/spam).
    This covers the separate case an editor can still hit: an explicitly-scored
    zero/near-zero confidence combined with a genuine low-confidence signal and
    every user-facing critical field (address/photo/hours) missing — a place an
    admin could confirm/publish with essentially no verifiable content behind it.

    Deliberately narrow: place.confidence is None for a freshly-created/
    not-yet-scored place (normal onboarding state, must not be blocked here).
    Only an explicitly recorded confidence <= 0 counts, and only combined with
    existence_confidence_level == "low" (a real negative signal, not the
    harmless "unknown" default every new place starts with).
    """
    failed: list[str] = []
    explicit_zero_confidence = place.confidence is not None and float(place.confidence) <= 0
    low_existence_confidence = place.existence_confidence_level == "low"
    missing_address = not place.address
    missing_photo = not place.image_url
    missing_hours = not place.opening_hours
    if explicit_zero_confidence and low_existence_confidence and missing_address and missing_photo and missing_hours:
        failed.append("zero_confidence_missing_critical_fields")
    return failed


def calculate_trust_score(place: Place) -> float:
    score = 0.0

    score += min(float(place.quality_score or 0), 40.0)
    if place.image_url:
        score += 15.0
    elif (place.photo_score or 0) > 0:
        score += 10.0

    description = place.short_description or ""
    if len(description.strip()) >= 100:
        score += 10.0
    elif description.strip():
        score += 5.0

    if place.address:
        score += 8.0
    if place.opening_hours:
        score += 7.0

    source = (place.source or "").lower()
    if "manual" in source or "admin" in source:
        score += 20.0
    elif "wikidata" in source:
        score += 15.0
    elif "osm" in source:
        score += 10.0
    elif source:
        score += 5.0

    if place.source_url:
        score += 5.0
    if (place.confidence_score or 0) >= 8 or (place.confidence or 0) >= 0.8:
        score += 5.0
    if place.verification_status == "verified" or place.existence_confidence_level == "high":
        score += 10.0
    if place.critical_field_expired:
        score -= 20.0

    return max(0.0, min(100.0, round(score, 2)))


def record_publication_decision(
    db: Session,
    place: Place,
    decision: PublicationDecision,
    *,
    config: PublicationPolicyConfig | None = None,
) -> PlacePublicationDecision:
    config = config or PublicationPolicyConfig()
    row = PlacePublicationDecision(
        city_id=place.city_id,
        place_id=place.id,
        mode=config.mode,
        decision=decision.decision,
        status="recorded",
        trust_score=decision.trust_score,
        failed_gates=decision.failed_gates,
        review_reasons=decision.review_reasons,
        payload={
            "title": place.title,
            "publication_status": place.publication_status,
            "auto_publish_enabled": config.auto_publish_enabled,
            "auto_publish_threshold": config.auto_publish_threshold,
        },
    )
    db.add(row)
    db.flush()
    return row


def apply_publication_decision(
    db: Session,
    place: Place,
    decision: PublicationDecision,
    *,
    config: PublicationPolicyConfig | None = None,
    actor: str = "publication-policy",
) -> PlacePublicationDecision:
    config = config or PublicationPolicyConfig()
    row = record_publication_decision(db, place, decision, config=config)

    if decision.should_publish:
        snapshot_place(db, place, reason="pre_auto_publish")
        place.status = "active"
        db.flush()
        try:
            transition_place_publication(
                db,
                place,
                to_status=PUBLISHED_STATUS,
                reason_code=REASON_PUBLISHED,
                actor=actor,
                source="publication_policy",
                human_comment=f"auto-published by {actor}: trust_score={decision.trust_score}",
                route_eligible_when_published=True,
            )
        except InvalidPublicationTransition:
            pass
        row.status = "applied"
    elif decision.decision in {DECISION_REVIEW, DECISION_HIDDEN, DECISION_SHADOW_AUTO_PUBLISH}:
        ensure_review_queue_item(db, place, decision)

    db.flush()
    return row


def snapshot_place(db: Session, place: Place, *, reason: str) -> PlaceSnapshot:
    row = PlaceSnapshot(place_id=place.id, reason=reason, snapshot_data=place_snapshot_payload(place))
    db.add(row)
    db.flush()
    return row


def place_snapshot_payload(place: Place) -> dict[str, object | None]:
    return {
        "title": place.title,
        "category_id": place.category_id,
        "category": place.category,
        "canonical_category": place.canonical_category,
        "lat": place.lat,
        "lng": place.lng,
        "address": place.address,
        "short_description": place.short_description,
        "image_url": place.image_url,
        "website": place.website,
        "phone": place.phone,
        "opening_hours": place.opening_hours,
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_route_eligible": place.is_route_eligible,
        "is_searchable": place.is_searchable,
        "publication_status": place.publication_status,
        "published_at": place.published_at.isoformat() if place.published_at else None,
    }


def _open_publication_review_item(db: Session, *, place_id: int, reason: str) -> ReviewQueueItem | None:
    return db.query(ReviewQueueItem).filter(
        ReviewQueueItem.place_id == place_id,
        ReviewQueueItem.field_name == "publication",
        ReviewQueueItem.reason == reason,
        ReviewQueueItem.status == "open",
    ).first()


def ensure_review_queue_item(db: Session, place: Place, decision: PublicationDecision) -> ReviewQueueItem:
    """Create or reuse the one open "publication" review item for this
    place+reason. The SELECT-then-INSERT below is not itself race-safe --
    the real guarantee is the partial unique index
    uq_review_queue_items_open_identity (migration a4c6e8f0b2d4) plus the
    SAVEPOINT/IntegrityError recovery here: on a concurrent-writer conflict
    only this insert attempt is rolled back (never the caller's own
    batch-owned outer transaction, see apply_publication_decision), and the
    row the winning writer actually created is re-selected and returned.

    The SAVEPOINT is opened on the raw Core Connection, not via
    db.begin_nested(): the ORM Session's own begin_nested() unconditionally
    flushes the session's entire pending unit of work first, which would
    prematurely persist unrelated in-flight Place mutations elsewhere in the
    same session. A Core-level insert executed directly on the connection
    avoids that flush and avoids the ORM Session being marked "pending
    rollback" on the IntegrityError.

    The NestedTransaction is used as a context manager (``with connection
    .begin_nested(): ...``), not via manual ``.commit()``/``.rollback()``
    calls guarded only by ``except IntegrityError`` -- the context manager
    form guarantees the SAVEPOINT is rolled back on ANY exception raised
    inside the block and released (committed) only on success, so a
    non-IntegrityError failure can never leave the SAVEPOINT dangling
    neither committed nor rolled back."""
    reason = decision.review_reasons[0] if decision.review_reasons else REASON_LOW_TRUST
    existing = _open_publication_review_item(db, place_id=place.id, reason=reason)
    if existing is not None:
        return existing
    row_values = dict(
        city_id=place.city_id,
        place_id=place.id,
        field_name="publication",
        reason=reason,
        severity="high" if decision.failed_gates else "medium",
        status="open",
        payload={
            "decision": decision.decision,
            "trust_score": decision.trust_score,
            "failed_gates": decision.failed_gates,
            "review_reasons": decision.review_reasons,
        },
    )
    connection = db.connection()
    new_id: int | None = None
    try:
        with connection.begin_nested():
            new_id = connection.execute(insert(ReviewQueueItem).values(**row_values)).inserted_primary_key[0]
    except IntegrityError:
        winner = _open_publication_review_item(db, place_id=place.id, reason=reason)
        if winner is None:
            raise
        return winner
    return db.query(ReviewQueueItem).filter(ReviewQueueItem.id == new_id).one()


def create_change_review(
    db: Session,
    place: Place,
    *,
    field_name: str,
    old_value: Any,
    new_value: Any,
    source: str = "import",
    confidence: float | None = None,
    config: PublicationPolicyConfig | None = None,
) -> PlaceChangeReview | None:
    if old_value == new_value:
        return None

    config = config or PublicationPolicyConfig()
    trust_score = calculate_trust_score(place)
    reason = change_review_reason(field_name, old_value=old_value, new_value=new_value, place=place, config=config)
    row = PlaceChangeReview(
        city_id=place.city_id,
        place_id=place.id,
        field_name=field_name,
        old_value=_json_value(old_value),
        new_value=_json_value(new_value),
        reason=reason,
        source=source,
        confidence=confidence,
        trust_score=trust_score,
        status="pending",
    )
    db.add(row)

    if reason in {REASON_CRITICAL_FIELD_CHANGED, REASON_NAME_CHANGE, REASON_CATEGORY_CHANGE, REASON_LOCATION_CHANGE, REASON_CLOSURE}:
        ensure_review_queue_item(
            db,
            place,
            PublicationDecision(
                decision=DECISION_KEEP_PUBLISHED,
                trust_score=trust_score,
                failed_gates=[],
                review_reasons=[reason],
            ),
        )
    elif config.mode == MODE_APPLY and config.auto_publish_enabled and field_name in AUTO_ACCEPT_FIELDS and trust_score >= config.auto_publish_threshold:
        _apply_auto_accept_field(place, field_name, new_value)
        row.status = "accepted"
        row.reviewed_by = "publication-policy"
        row.reviewed_at = datetime.utcnow()
        row.resolution = "auto_accepted"

    db.flush()
    return row


def change_review_reason(
    field_name: str,
    *,
    old_value: Any,
    new_value: Any,
    place: Place,
    config: PublicationPolicyConfig,
) -> str:
    if field_name in {"title", "name"}:
        return REASON_NAME_CHANGE
    if field_name in {"category", "canonical_category", "category_id"}:
        return REASON_CATEGORY_CHANGE
    if field_name in {"lat", "lng"}:
        return REASON_LOCATION_CHANGE
    if field_name == "address" and old_value:
        return REASON_ADDRESS_CHANGE
    if field_name == "lifecycle_status" and new_value in {"closed", "permanently_closed", "archived"}:
        return REASON_CLOSURE
    if field_name in CRITICAL_FIELDS:
        return REASON_CRITICAL_FIELD_CHANGED
    return REASON_LOW_TRUST


def _inside_city_bbox(place: Place, city: City) -> bool:
    bbox = city.bbox or {}
    if not bbox:
        return True

    min_lat = _first_number(bbox, "min_lat", "south", "s")
    max_lat = _first_number(bbox, "max_lat", "north", "n")
    min_lng = _first_number(bbox, "min_lng", "west", "w")
    max_lng = _first_number(bbox, "max_lng", "east", "e")
    if None in (min_lat, max_lat, min_lng, max_lng):
        return True
    return bool(min_lat <= place.lat <= max_lat and min_lng <= place.lng <= max_lng)


def _first_number(payload: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius = 6371000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return earth_radius * 2 * atan2(sqrt(a), sqrt(1 - a))
