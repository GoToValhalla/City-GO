"""Canonical public access loader for RouteDraft (hashed anonymous ownership).

Ownership model:
- Public endpoints have no trusted authenticated-user context.
- Ownership is session_token_hash only (compare via ownership_tokens_match).
- Request-supplied user_id is never accepted as proof of ownership.
- Credential transport: header X-Route-Draft-Session.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Query, Session

from models.city import City
from models.route_draft import RouteDraft
from services.anonymous_ownership import ownership_tokens_match
from services.route_draft_errors import RouteDraftError

SESSION_HEADER = "X-Route-Draft-Session"


def get_accessible_draft_or_error(
    db: Session,
    draft_id: int,
    *,
    session_token: str | None,
    for_update: bool = False,
) -> RouteDraft:
    """Load a draft only when hashed ownership + lifecycle allow access."""
    query: Query = db.query(RouteDraft).filter(RouteDraft.id == draft_id)
    if for_update:
        query = query.with_for_update()
    draft = query.first()
    if draft is None or not _lifecycle_ok(draft) or not _token_ok(draft, session_token):
        raise RouteDraftError("DRAFT_NOT_FOUND", "Draft not found", 404)
    city = db.query(City).filter(City.id == draft.city_id).first()
    if city is None or not bool(city.is_active) or city.launch_status != "published":
        raise RouteDraftError("DRAFT_NOT_FOUND", "Draft not found", 404)
    return draft


def _lifecycle_ok(draft: RouteDraft) -> bool:
    if str(draft.status or "") != "active":
        return False
    expires_at = draft.expires_at
    if expires_at is not None and expires_at < datetime.utcnow():
        return False
    return True


def _token_ok(draft: RouteDraft, session_token: str | None) -> bool:
    return ownership_tokens_match(session_token, draft.session_token_hash)
