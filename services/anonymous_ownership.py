"""Anonymous ownership credentials: issue, hash-at-rest, constant-time compare.

Public endpoints without trusted auth use high-entropy bearer tokens.
Raw tokens are never persisted; only digests are stored and compared.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException

DEFAULT_OWNERSHIP_HEADER = "X-Anonymous-Session"
ROUTE_SESSION_HEADER = "X-Route-Session"
ROUTE_DRAFT_HEADER = "X-Route-Draft-Session"


def issue_ownership_token(*, nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_ownership_token(token: str) -> str:
    normalized = str(token or "").strip()
    if not normalized:
        raise ValueError("ownership token must be non-empty")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ownership_tokens_match(provided: str | None, stored_hash: str | None) -> bool:
    provided_norm = str(provided or "").strip()
    stored_norm = str(stored_hash or "").strip()
    if not provided_norm or not stored_norm:
        return False
    try:
        digest = hash_ownership_token(provided_norm)
    except ValueError:
        return False
    return hmac.compare_digest(digest, stored_norm)


def require_ownership_header(
    value: str | None,
    *,
    header_name: str,
) -> str:
    """Return the raw header token or raise non-disclosing 404."""
    token = str(value or "").strip()
    if len(token) < 16:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Resource not found"},
        )
    return token


def anonymous_subject_from_token(token: str | None) -> str | None:
    """Map a raw anonymous token to a stable non-reversible subject id."""
    normalized = str(token or "").strip()
    if len(normalized) < 16:
        return None
    return f"anon:{hash_ownership_token(normalized)}"


def optional_anonymous_session(
    x_anonymous_session: str | None = Header(default=None, alias=DEFAULT_OWNERSHIP_HEADER),
) -> str | None:
    return anonymous_subject_from_token(x_anonymous_session)


def require_anonymous_session(
    x_anonymous_session: str | None = Header(default=None, alias=DEFAULT_OWNERSHIP_HEADER),
) -> str:
    subject = anonymous_subject_from_token(x_anonymous_session)
    if subject is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Resource not found"},
        )
    return subject
