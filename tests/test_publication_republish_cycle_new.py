from __future__ import annotations

import pytest

from services.admin_service import PlacePublicationBlockedError, publish_place, unpublish_place


def test_admin_unpublish_then_republish_is_recoverable(db_session, published_place_factory) -> None:
    place = published_place_factory(slug="republish-cycle", category="museum")

    unpublished = unpublish_place(
        db_session,
        place.id,
        actor="test-admin",
        reason="Временное снятие с публикации",
    )
    assert unpublished is not None
    assert unpublished.publication_status == "unpublished"
    assert unpublished.is_active is False
    assert unpublished.is_published is False

    republished = publish_place(
        db_session,
        place.id,
        actor="test-admin",
        reason="Возврат после проверки",
    )
    assert republished is not None
    assert republished.publication_status == "published"
    assert republished.is_active is True
    assert republished.is_published is True
    assert republished.is_visible_in_catalog is True
    assert republished.publication_reason_code is None


def test_product_inactive_status_still_blocks_publish(db_session, draft_place_factory) -> None:
    place = draft_place_factory(slug="inactive-product-block", category="museum")
    place.status = "inactive"
    db_session.commit()

    with pytest.raises(PlacePublicationBlockedError):
        publish_place(db_session, place.id, actor="test-admin", reason="must stay blocked")
