from models.place import Place
from models.review_queue_item import ReviewQueueItem
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
        lat=47.2357,
        lng=39.7015,
        status="active",
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_searchable=True,
        is_route_eligible=True,
        publication_status="published",
    )


def test_web_api_and_telegram_share_the_same_public_city_and_place_contract(
    client,
    db_session,
    city_factory,
) -> None:
    published_city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    draft_city = city_factory(slug="astrakhan", name="Астрахань", is_active=False, launch_status="draft")
    public_place = _public_place(published_city.id, "rostov-place")
    hidden_place = _public_place(draft_city.id, "astrakhan-place")
    db_session.add_all([public_place, hidden_place])
    db_session.commit()

    web_cities = client.get("/cities/available")
    web_places = client.get("/places/?limit=20")
    assert web_cities.status_code == 200
    assert [item["slug"] for item in web_cities.json()] == ["rostov"]
    assert web_places.status_code == 200
    assert [item["id"] for item in web_places.json()["items"]] == [public_place.id]
    assert client.get(f"/places/{hidden_place.id}").status_code == 404

    bot = BotFacade(db_session)
    assert [city.slug for city in bot.published_cities()] == ["rostov"]
    assert bot.place(public_place.id) is not None
    assert bot.place(hidden_place.id) is None


def test_changed_public_place_disappears_everywhere_until_rejected_change_is_rolled_back(
    client,
    db_session,
    city_factory,
) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place = _public_place(city.id, "rostov-place")
    db_session.add(place)
    db_session.flush()
    review = ReviewQueueItem(
        city_id=city.id,
        place_id=place.id,
        field_name="place_change",
        reason="source_data_changed",
        severity="medium",
        status="open",
        payload={
            "decision": "needs_review",
            "before_public": {
                "status": "active",
                "is_active": True,
                "is_published": True,
                "is_visible_in_catalog": True,
                "is_searchable": True,
                "is_route_eligible": True,
                "publication_status": "published",
            },
            "changes": {"title": {"before": "Старое", "after": "Новое"}},
        },
    )
    place.title = "Новое"
    place.status = "needs_review"
    place.is_active = False
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "needs_review"
    db_session.add(review)
    db_session.commit()

    assert client.get(f"/places/{place.id}").status_code == 404
    assert BotFacade(db_session).place(place.id) is None

    review_response = client.post(f"/admin/place-change-reviews/{review.id}/reject", json={"reason": "source is incorrect"})
    assert review_response.status_code == 200

    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id) is not None


def test_reconciliation_requires_no_auto_publication_and_supports_audited_rollback(
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

    result = apply_publication_reconciliation(db_session, actor="test-admin")
    assert result["changed_places"] == 1
    assert leaked.is_published is False
    assert draft.is_published is False

    rollback = rollback_publication_reconciliation(
        db_session,
        audit_ids=result["audit_ids"],
        actor="test-admin",
        reason="verify rollback path",
    )
    assert rollback["restored_places"] == 1
    assert leaked.is_published is True


def test_admin_approve_publishes_changed_place_in_web_and_telegram(
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
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "needs_review"
    db_session.add(place)
    db_session.flush()
    review = ReviewQueueItem(
        city_id=city.id,
        place_id=place.id,
        field_name="place_change",
        reason="source_data_changed",
        severity="medium",
        status="open",
        payload={"decision": "needs_review", "changes": {"title": {"before": "Старое", "after": "Новая версия"}}},
    )
    db_session.add(review)
    db_session.commit()

    response = client.post(f"/admin/place-change-reviews/{review.id}/approve", json={"reason": "verified source"})
    assert response.status_code == 200
    assert client.get(f"/places/{place.id}").status_code == 200
    assert BotFacade(db_session).place(place.id).title == "Новая версия"
