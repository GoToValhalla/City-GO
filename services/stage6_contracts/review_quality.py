from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.stage6_contracts.publication import PublicationTransitionCommand, transition_publication


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


@dataclass(frozen=True)
class PublicationReviewDecision:
    place: Place
    decision: ReviewDecision
    actor: str
    reason_code: str
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class QualityFinding:
    entity_type: str
    entity_id: str
    code: str
    severity: str
    blocks_publication: bool


def consume_publication_decision(
    db: Session, decision: PublicationReviewDecision,
) -> PlacePublicationTransition | None:
    """Publication alone translates an explicit review decision into state."""

    if decision.decision is ReviewDecision.DEFER:
        return None
    target = "published" if decision.decision is ReviewDecision.APPROVE else "rejected"
    return transition_publication(db, PublicationTransitionCommand(
        place=decision.place, to_status=target, reason_code=decision.reason_code,
        actor=decision.actor, source="publication_review", reason_details=decision.details,
    ))
