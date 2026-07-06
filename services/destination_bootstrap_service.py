from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from services.destination_admin_validation import validate_bbox

NO_SCOPES = "NO_SCOPES"
NO_ENABLED_SCOPES = "NO_ENABLED_SCOPES"
INVALID_SCOPE_GEOMETRY = "INVALID_SCOPE_GEOMETRY"


def destination_bootstrap_status(db: Session, destination: Destination) -> tuple[bool, list[str]]:
    scopes = db.query(DestinationScope).filter_by(destination_id=destination.id).all()
    enabled = [scope for scope in scopes if scope.enabled]
    blockers = []
    if not scopes:
        blockers.append(NO_SCOPES)
    if scopes and not enabled:
        blockers.append(NO_ENABLED_SCOPES)
    if any(not scope_has_valid_geometry(scope) for scope in enabled):
        blockers.append(INVALID_SCOPE_GEOMETRY)
    return not blockers, blockers


def scope_has_valid_geometry(scope: DestinationScope) -> bool:
    try:
        return validate_bbox(scope.bbox) is not None
    except Exception:
        return False
