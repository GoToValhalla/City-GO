"""Soft-delete Place and append-only publication ledger regressions."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.place_service import delete_place
from services.publication_state_writer import (
    InvalidPublicationTransition,
    REASON_ADMIN_HIDE,
    REASON_ADMIN_UNPUBLISH,
    transition_place_publication,
)


def test_delete_place_soft_hides_and_preserves_row(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="soft-delete-place", category="museum")
    place_id = place.id
    before = db_session.query(PlacePublicationTransition).filter_by(place_id=place_id).count()

    assert delete_place(db_session, place_id, actor="admin:test", reason="operator soft delete") is True
    db_session.expire_all()
    stored = db_session.query(Place).filter_by(id=place_id).one()
    after = db_session.query(PlacePublicationTransition).filter_by(place_id=place_id).count()

    assert stored.publication_status == "hidden"
    assert stored.publication_reason_code == REASON_ADMIN_HIDE
    assert stored.is_published is False
    assert stored.is_visible_in_catalog is False
    assert stored.is_searchable is False
    assert stored.is_route_eligible is False
    assert after == before + 1


def test_repeated_delete_place_is_truthful_noop(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="soft-delete-noop", category="museum")
    assert delete_place(db_session, place.id, actor="admin:test") is True
    count_after_first = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).count()
    updated_at = place.updated_at

    assert delete_place(db_session, place.id, actor="admin:test") is True
    db_session.refresh(place)
    count_after_second = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).count()

    assert count_after_second == count_after_first
    assert place.updated_at == updated_at
    assert place.publication_status == "hidden"


def test_exact_publication_noop_does_not_mutate_or_append(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="exact-noop-place", category="museum")
    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        human_comment="first",
        lock_place=False,
    )
    db_session.commit()
    db_session.refresh(place)
    before_count = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).count()
    before_updated = place.updated_at

    with pytest.raises(InvalidPublicationTransition, match="already matches target"):
        transition_place_publication(
            db_session,
            place,
            to_status="unpublished",
            reason_code=REASON_ADMIN_UNPUBLISH,
            actor="admin:test",
            source="admin_manual",
            human_comment="first",
            lock_place=False,
        )
    db_session.refresh(place)
    assert db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).count() == before_count
    assert place.updated_at == before_updated


def test_orm_ledger_update_is_rejected(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="ledger-update-reject", category="museum")
    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        lock_place=False,
    )
    db_session.commit()
    row = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    nested = db_session.begin_nested()
    row.reason_code = "tampered"
    with pytest.raises(RuntimeError, match="append-only"):
        db_session.flush()
    nested.rollback()


def test_orm_ledger_delete_is_rejected(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="ledger-delete-reject", category="museum")
    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        lock_place=False,
    )
    db_session.commit()
    row = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    nested = db_session.begin_nested()
    with pytest.raises(RuntimeError, match="append-only"):
        db_session.delete(row)
        db_session.flush()
    nested.rollback()


def test_bulk_ledger_update_is_rejected(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="ledger-bulk-update", category="museum")
    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        lock_place=False,
    )
    db_session.commit()
    nested = db_session.begin_nested()
    with pytest.raises((RuntimeError, StatementError)):
        db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).update(
            {"reason_code": "tampered"},
            synchronize_session=False,
        )
        db_session.flush()
    nested.rollback()


def test_bulk_ledger_delete_is_rejected(db_session: Session, published_place_factory) -> None:
    place = published_place_factory(slug="ledger-bulk-delete", category="museum")
    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        lock_place=False,
    )
    db_session.commit()
    nested = db_session.begin_nested()
    with pytest.raises((RuntimeError, StatementError)):
        db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).delete(
            synchronize_session=False
        )
        db_session.flush()
    nested.rollback()


def test_delete_place_rollback_restores_state_and_ledger(
    db_session: Session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="soft-delete-rollback", category="museum")
    place_id = place.id
    before_status = place.publication_status
    before_count = db_session.query(PlacePublicationTransition).filter_by(place_id=place_id).count()

    nested = db_session.begin_nested()
    assert delete_place(db_session, place_id, actor="admin:test", commit=False) is True
    nested.rollback()
    db_session.expire_all()

    restored = db_session.query(Place).filter_by(id=place_id).one()
    assert restored.publication_status == before_status
    assert restored.is_published is True
    assert db_session.query(PlacePublicationTransition).filter_by(place_id=place_id).count() == before_count
