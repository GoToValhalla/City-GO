"""Canonical public access loader for RouteDraft (anonymous session ownership).

Ownership model (Stage 3 correction):
- These public endpoints have no trusted authenticated-user context.
- Ownership is anonymous session_token only (compare via hmac.compare_digest).
- Request-supplied user_id is never accepted as proof of ownership.
- Credential transport for subsequent requests: header X-Route-Draft-Session
  (not query string). Create establishes the token in the request body.
"""

from __future__ import annotations

import hmac
from datetime import datetime

from sqlalchemy.orm import Session, Query

from models.city import City
from models.route_draft import RouteDraft
from services.route_draft_errors import RouteDraftError

SESSION_HEADER = "X-Route-Draft-Session"


def get_accessible_draft_or_error(
    db: Session,
    draft_id: int,
    *,
    session_token: str | None,
    for_update: bool = False,
) -> RouteDraft:
    """Load a draft only when anonymous ownership + lifecycle allow access.

    Inaccessible drafts always raise DRAFT_NOT_FOUND (404).
    """
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
    stored = str(draft.session_token or "").strip()
    provided = str(session_token or "").strip()
    if not stored or not provided:
        return False
    return hmac.compare_digest(stored, provided)
