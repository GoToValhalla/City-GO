from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.place import Place
from models.place_change_review import PlaceChangeReview
from services.publication_reconciliation_service import (
    apply_publication_reconciliation,
    publication_reconciliation_snapshot,
    rollback_publication_reconciliation,
)
from telegram_bot.services.facade import BotFacade


def _public_place(city_id: int, slug: str) -> Place:
    return Place(
        city_id=city_id,
        slug=slug,
        title=slug,
        lat=47.2,
        lng=39.7,
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_searchable=True,
        is_route_eligible=True,
        publication_status="published",
    )


def test_hidden_place_not_visible_in_public_catalog_or_telegram(db_session, city_factory) -> None:
    city = city_factory(slug="hidden-city", name="Hidden City", is_active=True, launch_status="published")
    place = _public_place(city.id, "hidden-place")
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "unpublished"
    db_session.add(place)
    db_session.commit()

    client = TestClient(app)
    assert client.get(f"/places/{place.id}").status_code == 404
    assert BotFacade(db_session).place(place.id) is None


def test_admin_approve_publishes_changed_place_in_web_and_telegram(client, db_session, city_factory) -> None:
    city = city_factory(slug="approved-city", name="Approved City", is_active=True, launch_status="published")
    place = _public_place(city.id, "approved-place")
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "needs_review"
    db_session.add(place)
    db_session.commit()

    assert client.get(f"/places/{place.id}").status_code == 404
    assert BotFacade(db_session).place(place.id) is None

    review = PlaceChangeReview(
        place_id=place.id,
        field_name="title",
        old_value="old",
        new_value="new",
        status="pending",
        source="test",
    )
    db_session.add(review)
    db_session.commit()

    review_response = client.post(f"/admin/place-change-reviews/{review.id}/approve", json={"reason": "source is correct"})
    assert review_response.status_code == 200

    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id) is not None


def test_admin_reject_keeps_existing_public_place_visible(client, db_session, city_factory) -> None:
    city = city_factory(slug="reject-city", name="Reject City", is_active=True, launch_status="published")
    place = _public_place(city.id, "reject-place")
    review = PlaceChangeReview(
        place_id=place.id,
        field_name="title",
        old_value="old",
        new_value="bad new",
        status="pending",
        source="test",
    )
    db_session.add_all([place, review])
    db_session.commit()

    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id) is not None

    review_response = client.post(f"/admin/place-change-reviews/{review.id}/reject", json={"reason": "source is incorrect"})
    assert review_response.status_code == 200

    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id) is not None


def test_reconciliation_is_non_destructive_by_default_and_destructive_mode_is_audited(
    db_session,
    city_factory,
) -> None:
    legacy_city = city_factory(slug="legacy", name="Легаси", is_active=False, launch_status="unpublished")
    draft_city = city_factory(slug="draft", name="Черновик", is_active=False, launch_status="draft")
    leaked = _public_place(legacy_city.id, "legacy-place")
    draft = Place(
        city_id=draft_city.id,
        slug="draft-place",
        title="Черновик",
        lat=47.2,
        lng=39.7,
        is_active=True,
        is_published=False,
        is_visible_in_catalog=False,
        is_searchable=False,
        is_route_eligible=False,
        publication_status="draft",
    )
    db_session.add_all([leaked, draft])
    db_session.commit()

    before = publication_reconciliation_snapshot(db_session)
    assert before["violations"]["places_public_in_unpublished_city"] == [leaked.id]

    default_result = apply_publication_reconciliation(db_session, actor="test-admin")
    assert default_result["changed_places"] == 0
    assert default_result["skipped_destructive"] == 1
    assert leaked.is_published is True
    assert draft.is_published is False

    destructive_result = apply_publication_reconciliation(
        db_session,
        actor="test-admin",
        allow_destructive=True,
        reason="verify destructive rollback path",
    )
    assert destructive_result["changed_places"] == 1
    assert leaked.is_published is False

    rollback = rollback_publication_reconciliation(
        db_session,
        audit_ids=destructive_result["audit_ids"],
        actor="test-admin",
        reason="verify rollback path",
    )
    assert rollback["restored_places"] == 1
    assert leaked.is_published is True


def test_admin_approve_publishes_changed_place_in_web_and_telegram_again(
    client,
    db_session,
    city_factory,
) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place = _public_place(city.id, "rostov-approved-change")
    place.title = "Новая версия"
    place.status = "needs_review"
    place.is_active = False
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_route_eligible = False
    place.is_searchable = False
    place.publication_status = "needs_review"
    db_session.add(place)
    db_session.commit()

    review = PlaceChangeReview(
        place_id=place.id,
        field_name="title",
        old_value="Старая версия",
        new_value="Новая версия",
        status="pending",
        source="test",
    )
    db_session.add(review)
    db_session.commit()

    response = client.post(f"/admin/place-change-reviews/{review.id}/approve", json={"reason": "ok"})
    assert response.status_code == 200
    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id) is not None
