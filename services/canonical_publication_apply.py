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
) -> str:
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
    _set_published(place, route_eligible=verdict.import_decision.is_route_eligible, reason=actor)
    return "auto_published" if verdict.import_decision.is_route_eligible else "limited_published"


def apply_admin_city_publication_place(place: Place, *, now: datetime, reason: str | None) -> None:
    verdict = evaluate_place_route_eligibility(place)
    _set_published(place, route_eligible=verdict.eligible, reason=reason, now=now)
    place.route_exclusion_reason = None if verdict.eligible else ",".join(verdict.reasons[:5])


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
