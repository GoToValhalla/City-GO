"""Canonical publication policy application.

PlacePublicationDecision remains policy-only evidence. Every live publication-state
mutation is delegated to services.publication_state_writer.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_decision import PlacePublicationDecision
from services.canonical_publication_guard import (
    CanonicalPublicationVerdict,
    assess_place_import_decision,
    evaluate_canonical_publication,
)
from services.place_publication_eligibility import place_publication_eligibility
from services.publication_reason_mapping import primary_publication_reason
from services.publication_state_writer import (
    REASON_POLICY_GATE_FAILED,
    REASON_PUBLISHED,
    InvalidPublicationTransition,
    reconcile_published_place_state,
    transition_place_publication,
)
from services.route_eligibility_policy import evaluate_place_route_eligibility

ROUTE_POLICY_EXCLUDED = "route_policy_excluded"


def _route_exclusion_reason(reasons: tuple[str, ...] | list[str]) -> str:
    return ",".join(list(reasons)[:5]) or ROUTE_POLICY_EXCLUDED


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
    """Apply the most restrictive current verdict under a row lock."""
    place = _lock_place(db, place)
    verdict = _effective_verdict(place, verdict)
    _record_decision(
        db,
        place,
        verdict,
        job_id=job_id,
        snapshot_id=snapshot_id,
        actor=actor,
        applied=not record_only,
    )

    if record_only:
        return _outcome_result(verdict.outcome)
    if verdict.outcome == "preserve_public":
        return "preserved_public"

    details = {
        "policy_reasons": list(verdict.reasons),
        "job_id": job_id,
        "snapshot_id": snapshot_id,
        "lineage": verdict.lineage,
        "import_decision": verdict.import_decision.decision,
        "import_reason": verdict.import_decision.reason,
    }
    correlation_id = str(job_id) if job_id is not None else None

    if verdict.outcome == "blocked":
        transition_place_publication(
            db,
            place,
            to_status="needs_review",
            reason_code=REASON_POLICY_GATE_FAILED,
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=verdict.reasons[0] if verdict.reasons else "blocked",
            correlation_id=correlation_id,
            lock_place=False,
        )
        return "blocked"
    if verdict.outcome == "reject":
        transition_place_publication(
            db,
            place,
            to_status="archived",
            reason_code=primary_publication_reason(verdict.reasons),
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=verdict.reasons[0] if verdict.reasons else "rejected",
            correlation_id=correlation_id,
            lock_place=False,
        )
        return "rejected"
    if verdict.outcome == "review":
        transition_place_publication(
            db,
            place,
            to_status="needs_review",
            reason_code=REASON_POLICY_GATE_FAILED,
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=verdict.reasons[0] if verdict.reasons else "needs_review",
            correlation_id=correlation_id,
            lock_place=False,
        )
        return "review_required"
    if verdict.outcome != "publish":
        raise InvalidPublicationTransition(f"unsupported canonical publication outcome: {verdict.outcome}")

    route_verdict = _route_eligibility_verdict_for_publish(place)
    exclusion = None if route_verdict.eligible else _route_exclusion_reason(route_verdict.reasons)
    if place.publication_status == "published" and place.is_published:
        reconcile_published_place_state(
            db,
            place,
            route_eligible=route_verdict.eligible,
            route_exclusion_reason=exclusion,
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=actor,
            correlation_id=correlation_id,
            lock_place=False,
        )
    else:
        transition_place_publication(
            db,
            place,
            to_status="published",
            reason_code=REASON_PUBLISHED,
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=actor,
            correlation_id=correlation_id,
            route_eligible_when_published=route_verdict.eligible,
            route_exclusion_reason_when_published=exclusion,
            lock_place=False,
        )
    return "auto_published" if route_verdict.eligible else "limited_published"


def apply_admin_city_publication_place(
    db: Session,
    place: Place,
    *,
    actor: str,
    source: str,
    reason: str | None,
    lock_place: bool = True,
    route_eligible_override: bool | None = None,
) -> None:
    """Publish or reconcile a currently eligible place without changing product lifecycle state."""
    if lock_place:
        place = _lock_place(db, place)
    eligibility = place_publication_eligibility(place)
    if not eligibility.eligible:
        raise InvalidPublicationTransition(
            "publication eligibility changed before lock: " + ", ".join(eligibility.reasons)
        )

    verdict = _route_eligibility_verdict_for_publish(place)
    route_eligible = verdict.eligible if route_eligible_override is None else bool(route_eligible_override)
    if route_eligible:
        exclusion = None
    elif route_eligible_override is False:
        exclusion = reason or "admin_route_disabled"
    else:
        exclusion = _route_exclusion_reason(verdict.reasons)

    reason_details = {
        "route_eligibility_reasons": list(verdict.reasons),
        "route_eligibility_policy_result": verdict.eligible,
        "route_eligibility_override": route_eligible_override,
    }
    if place.publication_status == "published" and place.is_published:
        reconcile_published_place_state(
            db,
            place,
            route_eligible=route_eligible,
            route_exclusion_reason=exclusion,
            actor=actor,
            source=source,
            reason_details=reason_details,
            human_comment=reason,
            lock_place=False,
        )
        return

    transition_place_publication(
        db,
        place,
        to_status="published",
        reason_code=REASON_PUBLISHED,
        actor=actor,
        source=source,
        human_comment=reason,
        reason_details=reason_details,
        route_eligible_when_published=route_eligible,
        route_exclusion_reason_when_published=exclusion,
        lock_place=False,
    )


def _lock_place(db: Session, place: Place) -> Place:
    if place.id is None:
        db.flush()
    return (
        db.query(Place)
        .filter(Place.id == place.id)
        .populate_existing()
        .with_for_update()
        .one()
    )


def _effective_verdict(
    place: Place,
    original: CanonicalPublicationVerdict,
) -> CanonicalPublicationVerdict:
    """Never promote a stale verdict; only retain it or move to a safer outcome."""
    if original.outcome == "reject":
        return original
    fresh_import = assess_place_import_decision(place)
    fresh = evaluate_canonical_publication(
        place,
        import_decision=fresh_import,
        evidence_allowed=True,
        preserve_public=original.outcome == "preserve_public",
    )
    if fresh.outcome == "reject":
        return fresh
    if original.outcome == "publish":
        return original
    if original.outcome == "preserve_public" and fresh.outcome in {"blocked", "review"}:
        return fresh
    return original


def _outcome_result(outcome: str) -> str:
    return {
        "preserve_public": "preserved_public",
        "publish": "review_required",
        "blocked": "blocked",
        "reject": "rejected",
        "review": "review_required",
    }.get(outcome, "review_required")


def _route_eligibility_verdict_for_publish(place: Place):
    if place.is_active and place.is_published and place.is_visible_in_catalog:
        return evaluate_place_route_eligibility(place)
    probe = Place(
        city_id=place.city_id,
        title=place.title,
        category=place.category,
        canonical_category=place.canonical_category or place.category,
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
    applied: bool,
) -> None:
    db.add(
        PlacePublicationDecision(
            city_id=place.city_id,
            place_id=place.id,
            mode="import_pipeline",
            decision=verdict.outcome,
            status="applied" if applied and verdict.outcome == "publish" else "recorded",
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
                "record_only": not applied,
            },
        )
    )
    db.flush()
