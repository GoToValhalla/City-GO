from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.publication_state_writer import transition_place_publication


@dataclass(frozen=True)
class PublicationTransitionCommand:
    place: Place
    to_status: str
    reason_code: str
    actor: str
    source: str
    reason_details: dict[str, object] | None = None


def transition_publication(db: Session, command: PublicationTransitionCommand) -> PlacePublicationTransition:
    """Delegate to the sole publication-state writer without committing."""

    return transition_place_publication(
        db, command.place, to_status=command.to_status, reason_code=command.reason_code,
        actor=command.actor, source=command.source, reason_details=command.reason_details,
    )
