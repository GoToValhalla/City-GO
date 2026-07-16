"""Canonical publication apply — the only writer for catalog visibility flags."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_decision import PlacePublicationDecision
from services.canonical_publication_guard import CanonicalPublicationVerdict
from services.route_eligibility_policy import evaluate_place_route_eligibility


def apply_canonical_publication_verdict(
    db: Session,
    place: Place,
    verdict: CanonicalPublicationVerdict,
    *,
    job_id: int | None,
    snapshot_id: int | None,
    actor: str = "import_pipeline",
    record_only: bool = False,
) -> str:
    """Apply a canonical publication verdict.

    CITYGO-339/341 + post-CITYGO-339..344 blocker fix: ``record_only=True``
    is used by every import-side call site — both the mid-pipeline
    ``apply_publication_decisions`` step (no evidence yet) and
    services/import_publication_finalize.py (real evidence exists, but a
    successful import may still only produce a publication PROPOSAL, never
    a live publish). In that mode this function must never auto-publish a
    place (never call _set_published) — that is the "publish" outcome
    these tickets name. Only an explicit admin action (services/
    admin_service.py's publish_place, services/admin_city_publication_service.py's
    publish_city) may call this with record_only=False.

    record_only does NOT suppress _set_review/_set_archived: hard safety
    rejection (invalid coordinates, hard-excluded categories, missing
    titles) and category/policy review-marks have always been allowed to
    hide/unpublish even an already-live place — see
    canonical_publication_guard.evaluate_canonical_publication's own
    "hard safety rejection always wins, even for an already-public place"
    contract, and tests/test_import_pipeline_foundation_safety.py, which
    locks in that a place with 0,0 coordinates or a pharmacy/bus_stop
    category must be archived/route-ineligible even mid-pipeline. That is
    quality enforcement, not the "publish" action CITYGO-339 targets.
    """
    _record_decision(db, place, verdict, job_id=job_id, snapshot_id=snapshot_id, actor=actor)
    if verdict.outcome == "preserve_public":
        return "preserved_public"
    if verdict.outcome == "blocked":
        _set_review(place, verdict.reasons[0] if verdict.reasons else "blocked")
        return "blocked"
    if verdict.outcome == "reject":
        _set_archived(place, verdict.reasons[0] if verdict.reasons else "rejected")
        return "rejected"
    if verdict.outcome == "review":
        _set_review(place, verdict.reasons[0] if verdict.reasons else "needs_review")
        return "review_required"
    if record_only:
        return "review_required"
    route_verdict = _route_eligibility_verdict_for_publish(place)
    _set_published(place, route_eligible=route_verdict.eligible, reason=actor)
    return "auto_published" if route_verdict.eligible else "limited_published"


def apply_admin_city_publication_place(place: Place, *, now: datetime, reason: str | None) -> None:
    """Stage 2 production validation blocker fix (found 2026-07-16): this
    used to call evaluate_place_route_eligibility(place) BEFORE the place
    was actually published (is_published/is_visible_in_catalog still
    False at that point), so the policy always saw a draft and returned
    eligible=False with reasons like draft_or_unpublished/
    not_visible_in_catalog — every place published through this function
    (both the single-place and city-wide admin paths) got
    is_route_eligible=False regardless of its real category/quality.
    _route_eligibility_verdict_for_publish() below already solves this
    exact problem correctly for the import-pipeline path via a probe
    object; reuse it here instead of duplicating the logic."""
    verdict = _route_eligibility_verdict_for_publish(place)
    _set_published(place, route_eligible=verdict.eligible, reason=reason, now=now)
    place.route_exclusion_reason = None if verdict.eligible else ",".join(verdict.reasons[:5])


def _route_eligibility_verdict_for_publish(place: Place):
    """Route eligibility must always come from route_eligibility_policy (the
    single source of truth for pharmacy/service/transport/etc. exclusion),
    never from the import quality gate's own category allowlist. The place
    is about to become active/published/visible, so evaluate eligibility as
    if those flags already hold — matching the pattern already used by
    place_publication_eligibility's own probe for the same reason."""
    if place.is_active and place.is_published and place.is_visible_in_catalog:
        return evaluate_place_route_eligibility(place)
    # Every field evaluate_place_route_eligibility reads must be copied from
    # the real place, defaulting only when the real place's own value is
    # None (an in-memory, not-yet-flushed Place() has None for every
    # column with a server-side default — getattr(place, name, default)
    # cannot help there since the attribute exists and is just None).
    probe = Place(
        city_id=place.city_id,
        title=place.title,
        category=place.category,
        canonical_category=place.canonical_category,
        place_layer=place.place_layer or "tourist_catalog",
        lat=place.lat,
        lng=place.lng,
        is_active=True,
        status=place.status or "active",
        internal_status=place.internal_status or "active",
        lifecycle_status=place.lifecycle_status or "active",
        is_published=True,
        is_visible_in_catalog=True,
        route_policy=place.route_policy or "city_walking",
        tourist_eligible=True if place.tourist_eligible is None else place.tourist_eligible,
        transport_required=bool(place.transport_required),
        quality_tier=place.quality_tier or "silver",
        publication_status="published",
        is_spam_poi=bool(getattr(place, "is_spam_poi", False)),
        is_duplicate_suspected=bool(getattr(place, "is_duplicate_suspected", False)),
        critical_field_expired=bool(getattr(place, "critical_field_expired", False)),
    )
    return evaluate_place_route_eligibility(probe)


def _record_decision(
    db: Session,
    place: Place,
    verdict: CanonicalPublicationVerdict,
    *,
    job_id: int | None,
    snapshot_id: int | None,
    actor: str,
) -> None:
    row = PlacePublicationDecision(
        city_id=place.city_id,
        place_id=place.id,
        mode="import_pipeline",
        decision=verdict.outcome,
        status="applied" if verdict.outcome == "publish" else "recorded",
        trust_score=float(place.confidence or 0.0),
        failed_gates=list(verdict.reasons),
        review_reasons=list(verdict.reasons),
        payload={
            "actor": actor,
            "job_id": job_id,
            "snapshot_id": snapshot_id,
            "lineage": verdict.lineage,
            "import_decision": verdict.import_decision.decision,
            "import_reason": verdict.import_decision.reason,
        },
    )
    db.add(row)
    db.flush()


def _set_published(place: Place, *, route_eligible: bool, reason: str | None, now: datetime | None = None) -> None:
    now = now or datetime.utcnow()
    place.is_active = True
    place.status = "active"
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.is_route_eligible = route_eligible
    place.publication_status = "published"
    place.publication_comment = reason
    place.published_at = place.published_at or now
    place.unpublished_at = None
    place.updated_at = now


def _set_review(place: Place, reason: str) -> None:
    place.is_active = True
    place.status = "active"
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "needs_review"
    place.publication_comment = reason
    place.updated_at = datetime.utcnow()


def _set_archived(place: Place, reason: str) -> None:
    place.is_active = False
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "archived"
    place.publication_comment = reason
    place.updated_at = datetime.utcnow()
