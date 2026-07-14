"""Canonical import/publication guard — single evaluation for every publish path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from models.place import Place
from services.import_publication_gate import assess_import_quality
from services.import_quality_categories import PublicationDecision
from services.place_publication_eligibility import READY_QUALITY_STATUS, SNAPSHOT_MAX_AGE, place_publication_eligibility

SUCCESS_IMPORT_STATUSES = frozenset({"success", "success_with_warnings"})
REJECT_IMPORT_REASONS = frozenset({"no_coordinates", "hidden_category", "no_title"})
# Category/policy concerns that must always route a changed place to manual
# review and create its review-queue item, even if the place is already
# public — unlike soft, data-completeness review reasons (no_source,
# low_confidence, missing_hours_for_dynamic_category), which the existing
# always-public contract lets an already-public place skip.
MANUAL_REVIEW_OVERRIDES_PRESERVE_PUBLIC = frozenset({"non_tourist_category"})


@dataclass(frozen=True)
class CanonicalPublicationVerdict:
    outcome: str
    reasons: tuple[str, ...]
    import_decision: PublicationDecision
    lineage: dict[str, object]


def assess_place_import_decision(place: Place) -> PublicationDecision:
    return assess_import_quality(
        title=place.title,
        lat=place.lat,
        lng=place.lng,
        category=place.category,
        confidence=place.confidence,
        source=place.source,
        address=place.address,
        opening_hours=place.opening_hours,
    )


def evaluate_canonical_publication(
    place: Place,
    *,
    import_decision: PublicationDecision,
    evidence_allowed: bool,
    preserve_public: bool = True,
) -> CanonicalPublicationVerdict:
    # Hard safety rejection always wins, even for an already-public place and
    # even when evidence_allowed is False: invalid coordinates, hidden
    # categories, missing titles, and other hard blockers must archive/hide
    # the place, never be shielded by preserve_public.
    if import_decision.reason in REJECT_IMPORT_REASONS or import_decision.decision == "hidden":
        return CanonicalPublicationVerdict(
            outcome="reject",
            reasons=(import_decision.reason,),
            import_decision=import_decision,
            lineage={"import_reason": import_decision.reason},
        )
    # preserve_public keeps an already-public place visible while flagged for
    # soft, data-completeness review reasons (no_source, low_confidence,
    # missing_hours_for_dynamic_category) or when the decision would
    # auto-publish anyway. It must never apply to a category/policy concern
    # (MANUAL_REVIEW_OVERRIDES_PRESERVE_PUBLIC) — those must still move the
    # place to needs_review and create its review queue item.
    if (
        preserve_public
        and import_decision.reason not in MANUAL_REVIEW_OVERRIDES_PRESERVE_PUBLIC
        and bool(place.is_published and place.is_visible_in_catalog)
    ):
        return CanonicalPublicationVerdict(
            outcome="preserve_public",
            reasons=("already_public",),
            import_decision=import_decision,
            lineage={"import_reason": import_decision.reason},
        )
    eligibility = place_publication_eligibility(_eligibility_probe(place, import_decision))
    if import_decision.decision == "auto_publish" and eligibility.eligible:
        # evidence_allowed only gates the auto-publish path: it exists to stop
        # a place going public before quality-snapshot evidence is ready. It
        # must never block genuine review-required flagging — a changed place
        # that needs manual review must still reach the "review" outcome
        # below and get its review queue item, regardless of evidence state.
        if not evidence_allowed:
            return CanonicalPublicationVerdict(
                outcome="blocked",
                reasons=("import_evidence_not_allowed",),
                import_decision=import_decision,
                lineage={"import_reason": import_decision.reason},
            )
        return CanonicalPublicationVerdict(
            outcome="publish",
            reasons=("quality_ok",),
            import_decision=import_decision,
            lineage={"import_reason": import_decision.reason},
        )
    review_reasons = (import_decision.reason,) if import_decision.decision == "needs_review" else eligibility.reasons
    return CanonicalPublicationVerdict(
        outcome="review",
        reasons=tuple(review_reasons) or ("needs_review",),
        import_decision=import_decision,
        lineage={"import_reason": import_decision.reason, "eligibility": eligibility.reasons},
    )


def import_evidence_allows_publish(
    *,
    job_status: str,
    snapshot_quality_status: str | None,
    snapshot_job_id: int | None,
    current_job_id: int,
    snapshot_created_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if job_status not in SUCCESS_IMPORT_STATUSES:
        reasons.append(f"import_status:{job_status}")
    if snapshot_quality_status != READY_QUALITY_STATUS:
        reasons.append(f"snapshot_quality:{snapshot_quality_status or 'missing'}")
    if snapshot_job_id != current_job_id:
        reasons.append("snapshot_job_mismatch")
    if snapshot_created_at is not None and (now or datetime.utcnow()) - snapshot_created_at > SNAPSHOT_MAX_AGE:
        reasons.append("stale_readiness_snapshot")
    return (not reasons, tuple(reasons))


def _eligibility_probe(place: Place, import_decision: PublicationDecision) -> Place:
    if place.is_active and import_decision.decision == "auto_publish":
        return place
    probe = Place(
        city_id=place.city_id,
        title=place.title,
        category=place.category,
        canonical_category=place.canonical_category,
        place_layer=place.place_layer,
        lat=place.lat,
        lng=place.lng,
        is_active=True,
        status=place.status or "active",
        is_spam_poi=bool(getattr(place, "is_spam_poi", False)),
        is_duplicate_suspected=bool(getattr(place, "is_duplicate_suspected", False)),
    )
    return probe
