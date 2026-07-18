from __future__ import annotations

import pytest

from models.place_publication_transition import PlacePublicationTransition
from services.admin_place_bulk_service import apply_bulk
from services.admin_place_update_service import (
    _ALLOWED,
    _PUBLICATION_CONTROLLED_FIELDS,
    update_admin_place_fields,
)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("is_active", False),
        ("status", "hidden"),
        ("publication_status", "hidden"),
        ("is_published", False),
        ("is_visible_in_catalog", False),
        ("is_searchable", False),
        ("is_route_eligible", False),
        ("visible_to_users", False),
        ("searchable", False),
        ("route_enabled", False),
        ("publication_reason_code", "admin_hide"),
        ("publication_reason_details", {"reason": "bypass"}),
        ("publication_comment", "bypass"),
    ],
)
def test_generic_admin_update_rejects_every_publication_controlled_field(
    db_session,
    published_place_factory,
    field: str,
    value: object,
) -> None:
    place = published_place_factory(slug=f"publication-boundary-{field.replace('_', '-')}")
    before = {
        "is_active": place.is_active,
        "status": place.status,
        "publication_status": place.publication_status,
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_searchable": place.is_searchable,
        "is_route_eligible": place.is_route_eligible,
        "publication_reason_code": place.publication_reason_code,
        "publication_reason_details": dict(place.publication_reason_details or {}),
        "publication_comment": place.publication_comment,
    }

    with pytest.raises(ValueError, match="Поля публикации нельзя изменять"):
        update_admin_place_fields(db_session, place.id, {field: value}, actor="test-admin")

    db_session.refresh(place)
    after = {
        "is_active": place.is_active,
        "status": place.status,
        "publication_status": place.publication_status,
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_searchable": place.is_searchable,
        "is_route_eligible": place.is_route_eligible,
        "publication_reason_code": place.publication_reason_code,
        "publication_reason_details": dict(place.publication_reason_details or {}),
        "publication_comment": place.publication_comment,
    }
    assert after == before


def test_generic_admin_update_allowlist_cannot_overlap_publication_state() -> None:
    assert _ALLOWED.isdisjoint(_PUBLICATION_CONTROLLED_FIELDS)


def test_generic_admin_update_still_updates_ordinary_fields(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="ordinary-admin-update", title="Старое название")

    updated = update_admin_place_fields(
        db_session,
        place.id,
        {"title": "Новое название", "admin_comment": "Проверено вручную"},
        actor="test-admin",
    )

    assert updated is not None
    assert updated.title == "Новое название"
    assert updated.admin_comment == "Проверено вручную"
    assert updated.publication_status == "published"
    assert updated.is_published is True
    assert updated.publication_reason_code is None


def test_bulk_category_update_uses_prelocked_non_committing_admin_update(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="bulk-category-update", category="museum")

    result = apply_bulk(
        db_session,
        [place.id],
        "set_category",
        {"category": "culture"},
        actor="test-admin",
    )

    assert result == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.category == "culture"
    assert place.canonical_category == "culture"
    assert place.publication_status == "published"
    assert place.is_published is True


def test_bulk_route_actions_use_writer_and_append_transition_ledger(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="bulk-route-writer", category="museum")
    initial_count = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .count()
    )

    disabled = apply_bulk(
        db_session,
        [place.id],
        "disable_route",
        {"reason": "Временно исключено администратором"},
        actor="test-admin",
    )
    enabled = apply_bulk(
        db_session,
        [place.id],
        "enable_route",
        {"reason": "Возвращено администратором"},
        actor="test-admin",
    )

    assert disabled["failed"] == 0
    assert enabled["failed"] == 0
    db_session.refresh(place)
    assert place.publication_status == "published"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True
    assert place.route_exclusion_reason is None

    transitions = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .order_by(PlacePublicationTransition.id.asc())
        .all()
    )
    assert len(transitions) == initial_count + 2
    assert transitions[-2].source == "admin_bulk_disable_route"
    assert transitions[-2].reason_details["route_eligibility_override"] is False
    assert transitions[-1].source == "admin_bulk_enable_route"
    assert transitions[-1].reason_details["route_eligibility_override"] is True
