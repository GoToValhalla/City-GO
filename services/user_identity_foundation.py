"""Safe identity helpers for the dark-launch user foundation.

This module deliberately does not implement live Telegram login. It only provides
hash-only identity representation and explicit audited link/conflict semantics.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.user_foundation import IdentityLinkEvent, TelegramIdentity, User


class IdentityConflictError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stable_identity_hash(raw_subject: str, *, provider: str) -> str:
    """Hash provider subject ids before storing or comparing them.

    This is intentionally deterministic for lookup. Raw provider ids must not be
    logged by callers and are not stored by this helper.
    """

    normalized = raw_subject.strip()
    if not normalized:
        raise ValueError("provider subject must not be empty")
    return hashlib.sha256(f"{provider}:{normalized}".encode("utf-8")).hexdigest()


def telegram_user_hash(telegram_user_id: int | str) -> str:
    return stable_identity_hash(str(telegram_user_id), provider="telegram")


def get_or_create_user(db: Session, *, status: str = "active") -> User:
    user = User(id=str(uuid.uuid4()), status=status, created_at=utc_now(), updated_at=utc_now())
    db.add(user)
    db.flush()
    return user


def get_or_create_telegram_identity(
    db: Session,
    *,
    telegram_user_id_hash: str,
    source: str = "unknown",
    username_hash: str | None = None,
) -> TelegramIdentity:
    existing = db.query(TelegramIdentity).filter(TelegramIdentity.telegram_user_id_hash == telegram_user_id_hash).one_or_none()
    if existing is not None:
        existing.last_seen_at = utc_now()
        return existing

    now = utc_now()
    identity = TelegramIdentity(
        id=str(uuid.uuid4()),
        telegram_user_id_hash=telegram_user_id_hash,
        username_hash=username_hash,
        source=source,
        first_seen_at=now,
        last_seen_at=now,
        notifications_allowed=False,
        status="active",
    )
    db.add(identity)
    db.flush()
    return identity


def link_telegram_identity_to_user(
    db: Session,
    *,
    telegram_identity: TelegramIdentity,
    user: User,
    method: str,
    request_id: str | None = None,
) -> IdentityLinkEvent:
    """Link Telegram identity to user or record explicit conflict.

    A Telegram identity already linked to user A is never silently moved to user B.
    """

    now = utc_now()
    if telegram_identity.user_id and telegram_identity.user_id != user.id:
        event = IdentityLinkEvent(
            id=str(uuid.uuid4()),
            user_id=user.id,
            from_identity_type="telegram",
            from_identity_id=telegram_identity.id,
            to_identity_type="user",
            to_identity_id=user.id,
            method=method,
            status="conflict",
            reason="telegram_identity_already_linked_to_different_user",
            request_id=request_id,
            created_at=now,
            resolved_at=now,
        )
        telegram_identity.status = "conflict"
        db.add(event)
        db.flush()
        raise IdentityConflictError("telegram identity is already linked to a different user")

    telegram_identity.user_id = user.id
    telegram_identity.linked_at = telegram_identity.linked_at or now
    telegram_identity.last_seen_at = now
    telegram_identity.status = "active"
    event = IdentityLinkEvent(
        id=str(uuid.uuid4()),
        user_id=user.id,
        from_identity_type="telegram",
        from_identity_id=telegram_identity.id,
        to_identity_type="user",
        to_identity_id=user.id,
        method=method,
        status="linked",
        request_id=request_id,
        created_at=now,
        resolved_at=now,
    )
    db.add(event)
    db.flush()
    return event
