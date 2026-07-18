"""Canonical publication policy application.

PlacePublicationDecision remains policy-only evidence. Every live publication-state
mutation is delegated to services.publication_state_writer.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_decision import PlacePublicationDecision
from services.canonical_publication_guard import CanonicalPublicationVerdict
from services.publication_reason_mapping import primary_publication_reason
from services.publication_state_writer import (
    REASON_POLICY_GATE_FAILED,
    REASON_PUBLISHED,
    transition_place_publication,
)
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
    """Record a policy decision and, when required, apply it through the writer."""

    _record_decision(db, place, verdict, job_id=job_id, snapshot_id=snapshot_id, actor=actor)
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
        )
        return "blocked"
    if verdict.outcome == "reject":
        transition_place_publication(
            db,
            place,
            to_status="hidden",
            reason_code=primary_publication_reason(verdict.reasons),
            actor=actor,
            source="publication_policy",
            reason_details=details,
            human_comment=verdict.reasons[0] if verdict.reasons else "rejected",
            correlation_id=correlation_id,
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
        )
        return "review_required"
    if record_only:
        return "review_required"

    route_verdict = _route_eligibility_verdict_for_publish(place)
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
    )
    place.route_exclusion_reason = None if route_verdict.eligible else ",".join(route_verdict.reasons[:5])
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
    """Publish one place through the authoritative writer without committing.

    ``route_eligible_override`` is reserved for an explicit audited admin route
    action. Normal publication always derives route eligibility from policy.
    """

    verdict = _route_eligibility_verdict_for_publish(place)
    route_eligible = verdict.eligible if route_eligible_override is None else bool(route_eligible_override)
    reason_details = {
        "route_eligibility_reasons": list(verdict.reasons),
        "route_eligibility_policy_result": verdict.eligible,
        "route_eligibility_override": route_eligible_override,
    }
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
        lock_place=lock_place,
    )
    place.status = "active"
    if route_eligible:
        place.route_exclusion_reason = None
    elif route_eligible_override is False:
        place.route_exclusion_reason = reason or "admin_route_disabled"
    else:
        place.route_exclusion_reason = ",".join(verdict.reasons[:5])


def _route_eligibility_verdict_for_publish(place: Place):
    if place.is_active and place.is_published and place.is_visible_in_catalog:
        return evaluate_place_route_eligibility(place)
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
