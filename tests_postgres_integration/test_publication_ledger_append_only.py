"""PostgreSQL append-only publication ledger and soft-delete contracts."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.place_service import delete_place
from services.publication_state_writer import REASON_ADMIN_UNPUBLISH, transition_place_publication
from tests_postgres_integration.conftest import make_published_place, unique_slug

POSTGRES_URL = os.getenv("CITYGO_POSTGRES_TEST_URL") or os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL.startswith(("postgresql", "postgres")),
    reason="CITYGO_POSTGRES_TEST_URL is required for real PostgreSQL ledger tests",
)


def _disable_ledger_triggers(session: Session) -> None:
    session.execute(text("ALTER TABLE place_publication_transitions DISABLE TRIGGER USER"))


def _enable_ledger_triggers(session: Session) -> None:
    session.execute(text("ALTER TABLE place_publication_transitions ENABLE TRIGGER USER"))


@pytest.fixture
def pg_place(pg_session: Session, pg_city, pg_category) -> Place:
    place = make_published_place(pg_session, city=pg_city, category=pg_category, slug=unique_slug("ledger"))
    yield place
    try:
        _disable_ledger_triggers(pg_session)
        pg_session.query(PlacePublicationTransition).filter(
            PlacePublicationTransition.place_id == place.id
        ).delete(synchronize_session=False)
        pg_session.query(Place).filter(Place.id == place.id).delete(synchronize_session=False)
        pg_session.commit()
    finally:
        _enable_ledger_triggers(pg_session)
        pg_session.commit()


def test_postgres_raw_ledger_update_is_rejected(pg_session: Session, pg_place: Place) -> None:
    transition_place_publication(
        pg_session,
        pg_place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="pg-test",
        source="postgres_test",
        lock_place=False,
    )
    pg_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.execute(
            text(
                "UPDATE place_publication_transitions "
                "SET reason_code = 'tampered' WHERE place_id = :place_id"
            ),
            {"place_id": pg_place.id},
        )
        pg_session.commit()
    pg_session.rollback()


def test_postgres_raw_ledger_delete_is_rejected(pg_session: Session, pg_place: Place) -> None:
    transition_place_publication(
        pg_session,
        pg_place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="pg-test",
        source="postgres_test",
        lock_place=False,
    )
    pg_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.execute(
            text("DELETE FROM place_publication_transitions WHERE place_id = :place_id"),
            {"place_id": pg_place.id},
        )
        pg_session.commit()
    pg_session.rollback()


def test_postgres_fk_prevents_hard_delete_of_place_with_history(
    pg_session: Session,
    pg_place: Place,
) -> None:
    transition_place_publication(
        pg_session,
        pg_place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="pg-test",
        source="postgres_test",
        lock_place=False,
    )
    pg_session.commit()
    history = pg_session.query(PlacePublicationTransition).filter_by(place_id=pg_place.id).count()
    assert history >= 1
    with pytest.raises((IntegrityError, DBAPIError)):
        pg_session.execute(text("DELETE FROM places WHERE id = :place_id"), {"place_id": pg_place.id})
        pg_session.commit()
    pg_session.rollback()
    assert pg_session.query(Place).filter_by(id=pg_place.id).one() is not None
    assert (
        pg_session.query(PlacePublicationTransition).filter_by(place_id=pg_place.id).count() == history
    )


def test_postgres_soft_delete_preserves_place_and_history(
    pg_session: Session,
    pg_place: Place,
) -> None:
    transition_place_publication(
        pg_session,
        pg_place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="pg-test",
        source="postgres_test",
        lock_place=False,
    )
    pg_session.commit()
    before = pg_session.query(PlacePublicationTransition).filter_by(place_id=pg_place.id).count()

    assert delete_place(pg_session, pg_place.id, actor="pg-test", commit=True) is True
    pg_session.expire_all()
    stored = pg_session.query(Place).filter_by(id=pg_place.id).one()
    after = pg_session.query(PlacePublicationTransition).filter_by(place_id=pg_place.id).count()

    assert stored.publication_status == "hidden"
    assert after == before + 1
