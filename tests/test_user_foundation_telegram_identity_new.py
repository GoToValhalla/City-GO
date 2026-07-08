from __future__ import annotations

import pytest

from models.user_foundation import IdentityLinkEvent, TelegramIdentity
from services.user_identity_foundation import (
    IdentityConflictError,
    get_or_create_telegram_identity,
    get_or_create_user,
    link_telegram_identity_to_user,
    stable_identity_hash,
    telegram_user_hash,
)


def test_telegram_user_hash_is_stable_and_provider_scoped_new() -> None:
    assert telegram_user_hash(12345) == telegram_user_hash("12345")
    assert telegram_user_hash(12345) != stable_identity_hash("12345", provider="google")


def test_same_telegram_user_hash_maps_to_same_identity_new(db_session) -> None:
    subject_hash = telegram_user_hash(12345)

    first = get_or_create_telegram_identity(db_session, telegram_user_id_hash=subject_hash, source="bot")
    second = get_or_create_telegram_identity(db_session, telegram_user_id_hash=subject_hash, source="mini_app")

    assert first.id == second.id
    assert db_session.query(TelegramIdentity).filter(TelegramIdentity.telegram_user_id_hash == subject_hash).count() == 1


def test_telegram_identity_links_to_user_with_event_new(db_session) -> None:
    user = get_or_create_user(db_session)
    identity = get_or_create_telegram_identity(db_session, telegram_user_id_hash=telegram_user_hash(111), source="bot")

    event = link_telegram_identity_to_user(
        db_session,
        telegram_identity=identity,
        user=user,
        method="bot_start_link",
        request_id="req-1",
    )

    assert identity.user_id == user.id
    assert event.status == "linked"
    assert event.from_identity_type == "telegram"
    assert event.to_identity_type == "user"
    assert event.request_id == "req-1"


def test_telegram_identity_cannot_silently_link_to_two_users_new(db_session) -> None:
    user_a = get_or_create_user(db_session)
    user_b = get_or_create_user(db_session)
    identity = get_or_create_telegram_identity(db_session, telegram_user_id_hash=telegram_user_hash(222), source="bot")
    link_telegram_identity_to_user(db_session, telegram_identity=identity, user=user_a, method="bot_start_link")

    with pytest.raises(IdentityConflictError):
        link_telegram_identity_to_user(db_session, telegram_identity=identity, user=user_b, method="telegram_init_data")

    assert identity.user_id == user_a.id
    assert identity.status == "conflict"
    conflict = db_session.query(IdentityLinkEvent).filter(IdentityLinkEvent.status == "conflict").one()
    assert conflict.reason == "telegram_identity_already_linked_to_different_user"


def test_device_identity_and_telegram_identity_can_coexist_without_forced_merge_new(db_session) -> None:
    # Schema/service proof: creating a Telegram identity does not require anonymous identity
    # and does not force a canonical user until explicit link is requested.
    identity = get_or_create_telegram_identity(db_session, telegram_user_id_hash=telegram_user_hash(333), source="mini_app")

    assert identity.user_id is None
    assert db_session.query(IdentityLinkEvent).count() == 0
