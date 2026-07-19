from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition

PUBLISHED_STATUS = "published"

REASON_PUBLISHED = "published"
REASON_IMPORT_DRAFT = "import_draft"
REASON_IMPORT_INCOMPLETE = "import_incomplete"
REASON_ENRICHMENT_BACKLOG = "enrichment_backlog"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_POLICY_GATE_FAILED = "policy_gate_failed"
REASON_NEEDS_MANUAL_REVIEW = "needs_manual_review"
REASON_DUPLICATE_SUSPECTED = "duplicate_suspected"
REASON_SPAM_SUSPECTED = "spam_suspected"
REASON_NON_PUBLIC_CATEGORY = "non_public_category"
REASON_MISSING_COORDINATES = "missing_coordinates"
REASON_STALE_READINESS_SNAPSHOT = "stale_readiness_snapshot"
REASON_CITY_PUBLICATION_QUALITY_GATE = "city_publication_quality_gate"
REASON_ADMIN_CREATE_DRAFT = "admin_create_draft"
REASON_ADMIN_UNPUBLISH = "admin_unpublish"
REASON_ADMIN_REJECT = "admin_reject"
REASON_ADMIN_HIDE = "admin_hide"
REASON_ADMIN_DEFER = "admin_defer"
REASON_REPAIR_STATE = "repair_state"
REASON_LEGACY_UNKNOWN = "legacy_unknown"

CANONICAL_PUBLICATION_REASON_CODES = frozenset({
    REASON_PUBLISHED, REASON_IMPORT_DRAFT, REASON_IMPORT_INCOMPLETE,
    REASON_ENRICHMENT_BACKLOG, REASON_LOW_CONFIDENCE, REASON_POLICY_GATE_FAILED,
    REASON_NEEDS_MANUAL_REVIEW, REASON_DUPLICATE_SUSPECTED,
    REASON_SPAM_SUSPECTED, REASON_NON_PUBLIC_CATEGORY,
    REASON_MISSING_COORDINATES, REASON_STALE_READINESS_SNAPSHOT,
    REASON_CITY_PUBLICATION_QUALITY_GATE, REASON_ADMIN_CREATE_DRAFT,
    REASON_ADMIN_UNPUBLISH, REASON_ADMIN_REJECT, REASON_ADMIN_HIDE,
    REASON_ADMIN_DEFER, REASON_REPAIR_STATE, REASON_LEGACY_UNKNOWN,
})

_ALLOWED_TARGETS: Mapping[str, frozenset[str]] = {
    REASON_PUBLISHED: frozenset({"published"}),
    REASON_IMPORT_DRAFT: frozenset({"draft"}),
    REASON_IMPORT_INCOMPLETE: frozenset({"draft", "auto_backlog", "needs_review", "hidden"}),
    REASON_ENRICHMENT_BACKLOG: frozenset({"auto_backlog", "deferred"}),
    REASON_LOW_CONFIDENCE: frozenset({"low_confidence", "auto_backlog", "needs_review", "needs_manual_review"}),
    REASON_POLICY_GATE_FAILED: frozenset({"auto_backlog", "needs_review", "needs_manual_review", "hidden"}),
    REASON_NEEDS_MANUAL_REVIEW: frozenset({"needs_review", "needs_manual_review", "deferred"}),
    REASON_DUPLICATE_SUSPECTED: frozenset({"needs_review", "needs_manual_review", "hidden", "rejected"}),
    REASON_SPAM_SUSPECTED: frozenset({"needs_review", "needs_manual_review", "hidden", "rejected"}),
    REASON_NON_PUBLIC_CATEGORY: frozenset({"hidden", "deferred", "needs_review", "draft"}),
    REASON_MISSING_COORDINATES: frozenset({"draft", "auto_backlog", "needs_review", "hidden"}),
    REASON_STALE_READINESS_SNAPSHOT: frozenset({"deferred", "needs_review", "auto_backlog"}),
    REASON_CITY_PUBLICATION_QUALITY_GATE: frozenset({"needs_review", "needs_manual_review", "hidden", "unpublished", "deferred"}),
    REASON_ADMIN_CREATE_DRAFT: frozenset({"draft"}),
    REASON_ADMIN_UNPUBLISH: frozenset({"unpublished"}),
    REASON_ADMIN_REJECT: frozenset({"rejected"}),
    REASON_ADMIN_HIDE: frozenset({"hidden"}),
    REASON_ADMIN_DEFER: frozenset({"deferred", "needs_review", "needs_manual_review", "draft"}),
    REASON_REPAIR_STATE: frozenset({"draft", "auto_backlog", "low_confidence", "needs_review", "needs_manual_review", "deferred", "hidden", "unpublished", "rejected"}),
    REASON_LEGACY_UNKNOWN: frozenset({"draft", "auto_backlog", "low_confidence", "needs_review", "needs_manual_review", "deferred", "hidden", "unpublished", "rejected"}),
}


@dataclass(frozen=True)
class PublicationStateFlags:
    is_active: bool
    is_published: bool
    is_visible_in_catalog: bool
    is_searchable: bool


_STATE_FLAGS: Mapping[str, PublicationStateFlags] = {
    "published": PublicationStateFlags(True, True, True, True),
    "draft": PublicationStateFlags(True, False, False, False),
    "auto_backlog": PublicationStateFlags(True, False, False, False),
    "low_confidence": PublicationStateFlags(True, False, False, False),
    "needs_review": PublicationStateFlags(True, False, False, False),
    "needs_manual_review": PublicationStateFlags(True, False, False, False),
    "deferred": PublicationStateFlags(True, False, False, False),
    "hidden": PublicationStateFlags(False, False, False, False),
    "unpublished": PublicationStateFlags(False, False, False, False),
    "rejected": PublicationStateFlags(False, False, False, False),
}


class InvalidPublicationTransition(ValueError):
    pass


def transition_place_publication(
    db: Session,
    place: Place,
    *,
    to_status: str,
    reason_code: str,
    actor: str,
    source: str,
    reason_details: Mapping[str, object] | None = None,
    human_comment: str | None = None,
    correlation_id: str | None = None,
    route_eligible_when_published: bool | None = None,
    route_exclusion_reason_when_published: str | None = None,
    lock_place: bool = True,
) -> PlacePublicationTransition:
    """Apply the complete publication read model and append history; never commit."""
    _validate_transition_input(
        to_status=to_status,
        reason_code=reason_code,
        actor=actor,
        source=source,
        route_eligible_when_published=route_eligible_when_published,
        route_exclusion_reason_when_published=route_exclusion_reason_when_published,
    )
    place = _prepare_place(db, place, lock_place=lock_place)

    from_status = str(place.publication_status or "draft")
    details = dict(reason_details or {})
    flags = _STATE_FLAGS[to_status]
    if _matches_target_state(
        place,
        to_status=to_status,
        reason_code=reason_code,
        reason_details=details,
        human_comment=human_comment,
        route_eligible_when_published=route_eligible_when_published,
        route_exclusion_reason_when_published=route_exclusion_reason_when_published,
    ):
        raise InvalidPublicationTransition("publication state already matches target")

    now = datetime.now(timezone.utc)
    place.publication_status = to_status
    place.is_active = flags.is_active
    place.is_published = flags.is_published
    place.is_visible_in_catalog = flags.is_visible_in_catalog
    place.is_searchable = flags.is_searchable
    place.publication_comment = human_comment
    place.updated_at = now

    if to_status == PUBLISHED_STATUS:
        place.publication_reason_code = None
        place.publication_reason_details = {}
        place.unpublished_at = None
        place.published_at = place.published_at or now
        place.is_route_eligible = bool(route_eligible_when_published)
        place.route_exclusion_reason = (
            None if place.is_route_eligible else str(route_exclusion_reason_when_published)
        )
    else:
        place.publication_reason_code = reason_code
        place.publication_reason_details = details
        place.is_route_eligible = False
        place.route_exclusion_reason = reason_code
        place.unpublished_at = now

    transition = _append_transition(
        db,
        place=place,
        from_status=from_status,
        to_status=to_status,
        reason_code=reason_code,
        reason_details=details,
        human_comment=human_comment,
        actor=actor,
        source=source,
        correlation_id=correlation_id,
    )
    db.flush()
    return transition


def reconcile_published_place_state(
    db: Session,
    place: Place,
    *,
    route_eligible: bool,
    route_exclusion_reason: str | None,
    actor: str,
    source: str,
    reason_details: Mapping[str, object] | None = None,
    human_comment: str | None = None,
    correlation_id: str | None = None,
    lock_place: bool = True,
) -> bool:
    """Repair or update an already-published read model; append history only on change."""
    if not str(actor or "").strip():
        raise InvalidPublicationTransition("publication transition actor is required")
    if not str(source or "").strip():
        raise InvalidPublicationTransition("publication transition source is required")
    if route_eligible and route_exclusion_reason:
        raise InvalidPublicationTransition("route-eligible published place cannot have an exclusion reason")
    if not route_eligible and not str(route_exclusion_reason or "").strip():
        raise InvalidPublicationTransition("route-ineligible published place requires an exclusion reason")

    place = _prepare_place(db, place, lock_place=lock_place)
    if str(place.publication_status or "") != PUBLISHED_STATUS or not bool(place.is_published):
        raise InvalidPublicationTransition("published-state reconciliation requires a published place")

    target_exclusion = None if route_eligible else str(route_exclusion_reason)
    unchanged = (
        bool(place.is_active)
        and bool(place.is_published)
        and bool(place.is_visible_in_catalog)
        and bool(place.is_searchable)
        and place.publication_reason_code is None
        and dict(place.publication_reason_details or {}) == {}
        and place.unpublished_at is None
        and bool(place.is_route_eligible) is bool(route_eligible)
        and place.route_exclusion_reason == target_exclusion
        and place.published_at is not None
    )
    if unchanged:
        return False

    now = datetime.now(timezone.utc)
    previous_route = {
        "is_route_eligible": bool(place.is_route_eligible),
        "route_exclusion_reason": place.route_exclusion_reason,
    }
    place.publication_status = PUBLISHED_STATUS
    place.is_active = True
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.publication_reason_code = None
    place.publication_reason_details = {}
    place.unpublished_at = None
    place.published_at = place.published_at or now
    place.is_route_eligible = bool(route_eligible)
    place.route_exclusion_reason = target_exclusion
    place.updated_at = now

    details = dict(reason_details or {})
    details["previous_route_state"] = previous_route
    details["target_route_state"] = {
        "is_route_eligible": bool(route_eligible),
        "route_exclusion_reason": target_exclusion,
    }
    _append_transition(
        db,
        place=place,
        from_status=PUBLISHED_STATUS,
        to_status=PUBLISHED_STATUS,
        reason_code=REASON_PUBLISHED,
        reason_details=details,
        human_comment=human_comment,
        actor=actor,
        source=source,
        correlation_id=correlation_id,
    )
    db.flush()
    return True


def transition_locked_places_publication(
    db: Session,
    places: list[Place],
    *,
    to_status: str,
    reason_code: str,
    actor: str,
    source: str,
    reason_details: Mapping[str, object] | None = None,
    human_comment: str | None = None,
    correlation_id: str | None = None,
    route_eligible_when_published: bool | None = None,
    route_exclusion_reason_when_published: str | None = None,
) -> list[PlacePublicationTransition]:
    ordered_places = sorted(places, key=lambda item: int(item.id))
    if [int(item.id) for item in places] != [int(item.id) for item in ordered_places]:
        raise InvalidPublicationTransition("bulk publication places must be locked in ascending Place.id order")
    return [
        transition_place_publication(
            db,
            place,
            to_status=to_status,
            reason_code=reason_code,
            actor=actor,
            source=source,
            reason_details=reason_details,
            human_comment=human_comment,
            correlation_id=correlation_id,
            route_eligible_when_published=route_eligible_when_published,
            route_exclusion_reason_when_published=route_exclusion_reason_when_published,
            lock_place=False,
        )
        for place in ordered_places
    ]


def _validate_transition_input(
    *,
    to_status: str,
    reason_code: str,
    actor: str,
    source: str,
    route_eligible_when_published: bool | None,
    route_exclusion_reason_when_published: str | None,
) -> None:
    if to_status not in _STATE_FLAGS:
        raise InvalidPublicationTransition(f"unknown publication status: {to_status}")
    allowed_targets = _ALLOWED_TARGETS.get(reason_code)
    if allowed_targets is None or to_status not in allowed_targets:
        raise InvalidPublicationTransition(
            f"reason code {reason_code} is not allowed for target status {to_status}"
        )
    if not str(actor or "").strip():
        raise InvalidPublicationTransition("publication transition actor is required")
    if not str(source or "").strip():
        raise InvalidPublicationTransition("publication transition source is required")
    if to_status == PUBLISHED_STATUS:
        if route_eligible_when_published is None:
            raise InvalidPublicationTransition("published transition requires an explicit route verdict")
        if bool(route_eligible_when_published) and route_exclusion_reason_when_published:
            raise InvalidPublicationTransition("route-eligible published place cannot have an exclusion reason")
        if not bool(route_eligible_when_published) and not str(route_exclusion_reason_when_published or "").strip():
            raise InvalidPublicationTransition("route-ineligible published place requires an exclusion reason")


def _matches_target_state(
    place: Place,
    *,
    to_status: str,
    reason_code: str,
    reason_details: Mapping[str, object],
    human_comment: str | None,
    route_eligible_when_published: bool | None,
    route_exclusion_reason_when_published: str | None,
) -> bool:
    flags = _STATE_FLAGS[to_status]
    common = (
        str(place.publication_status or "draft") == to_status
        and bool(place.is_active) is flags.is_active
        and bool(place.is_published) is flags.is_published
        and bool(place.is_visible_in_catalog) is flags.is_visible_in_catalog
        and bool(place.is_searchable) is flags.is_searchable
        and place.publication_comment == human_comment
    )
    if not common:
        return False
    if to_status == PUBLISHED_STATUS:
        target_exclusion = (
            None if bool(route_eligible_when_published) else str(route_exclusion_reason_when_published)
        )
        return (
            place.publication_reason_code is None
            and dict(place.publication_reason_details or {}) == {}
            and place.unpublished_at is None
            and place.published_at is not None
            and bool(place.is_route_eligible) is bool(route_eligible_when_published)
            and place.route_exclusion_reason == target_exclusion
        )
    return (
        place.publication_reason_code == reason_code
        and dict(place.publication_reason_details or {}) == dict(reason_details)
        and not bool(place.is_route_eligible)
        and place.route_exclusion_reason == reason_code
        and place.unpublished_at is not None
    )


def _prepare_place(db: Session, place: Place, *, lock_place: bool) -> Place:
    if place.id is None:
        db.flush()
    if not lock_place:
        return place
    return (
        db.query(Place)
        .filter(Place.id == place.id)
        .populate_existing()
        .with_for_update()
        .one()
    )


def _append_transition(
    db: Session,
    *,
    place: Place,
    from_status: str,
    to_status: str,
    reason_code: str,
    reason_details: Mapping[str, object],
    human_comment: str | None,
    actor: str,
    source: str,
    correlation_id: str | None,
) -> PlacePublicationTransition:
    transition = PlacePublicationTransition(
        place_id=place.id,
        from_status=from_status,
        to_status=to_status,
        reason_code=reason_code,
        reason_details=dict(reason_details),
        human_comment=human_comment,
        actor=actor,
        source=source,
        correlation_id=correlation_id,
    )
    db.add(transition)
    return transition
