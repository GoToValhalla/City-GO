from __future__ import annotations

import pytest

from models.place_publication_transition import PlacePublicationTransition
from services.admin_place_bulk_service import apply_bulk
from services.admin_place_update_service import (
    _ALLOWED,
    _PUBLICATION_CONTROLLED_FIELDS,
    update_admin_place_fields,
)
from services.publication_state_ownership import PUBLICATION_CONTROLLED_INPUT_FIELDS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("is_active", False),
        ("publication_status", "hidden"),
        ("is_published", False),
        ("is_visible_in_catalog", False),
        ("is_searchable", False),
        ("is_route_eligible", False),
        ("visible_to_users", False),
        ("searchable", False),
        ("route_enabled", False),
        ("published_at", None),
        ("unpublished_at", None),
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
    assert _PUBLICATION_CONTROLLED_FIELDS == PUBLICATION_CONTROLLED_INPUT_FIELDS
    assert _ALLOWED.isdisjoint(PUBLICATION_CONTROLLED_INPUT_FIELDS)


def test_admin_patch_api_rejects_publication_state_changes(
    client,
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="admin-patch-publication-bypass")
    response = client.patch(
        f"/admin/places/{place.id}",
        json={"publication_status": "hidden", "visible_to_users": False},
    )
    assert response.status_code == 422
    assert "Поля публикации нельзя изменять" in response.json()["detail"]
    db_session.refresh(place)
    assert place.publication_status == "published"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True


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


def test_bulk_category_update_recalculates_publication_for_excluded_category(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="bulk-category-excluded", category="museum")
    result = apply_bulk(
        db_session,
        [place.id],
        "set_category",
        {"category": "transport"},
        actor="test-admin",
    )
    assert result == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.category == "transport"
    assert place.publication_status == "needs_review"
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
    assert place.publication_reason_code == "non_public_category"


def test_bulk_category_update_recalculates_route_for_safe_category(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="bulk-category-safe", category="museum")
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
    assert place.publication_status == "published"
    assert place.is_published is True


def test_bulk_route_actions_use_writer_and_append_transition_ledger(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="bulk-route-writer", category="museum")
    initial_count = db_session.query(PlacePublicationTransition).filter(
        PlacePublicationTransition.place_id == place.id
    ).count()

    disabled = apply_bulk(
        db_session,
        [place.id],
        "disable_route",
        {"reason": "Временно исключено администратором"},
        actor="test-admin",
    )
    assert disabled == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.is_route_eligible is False
    assert place.route_exclusion_reason == "Временно исключено администратором"

    enabled = apply_bulk(
        db_session,
        [place.id],
        "enable_route",
        {"reason": "Возвращено администратором"},
        actor="test-admin",
    )
    assert enabled == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.publication_status == "published"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True
    assert place.route_exclusion_reason is None

    transitions = db_session.query(PlacePublicationTransition).filter(
        PlacePublicationTransition.place_id == place.id
    ).order_by(PlacePublicationTransition.id.asc()).all()
    assert len(transitions) == initial_count + 2
    assert transitions[-2].source == "admin_bulk_disable_route"
    assert transitions[-2].reason_details["route_eligibility_override"] is False
    assert transitions[-1].source == "admin_bulk_enable_route"
    assert transitions[-1].reason_details["route_eligibility_override"] is True


def test_bulk_route_noop_is_reported_as_failure(db_session, published_place_factory) -> None:
    place = published_place_factory(slug="bulk-route-noop", category="museum")
    result = apply_bulk(
        db_session,
        [place.id],
        "enable_route",
        {"reason": "already enabled"},
        actor="test-admin",
    )
    assert result["applied"] == 0
    assert result["failed"] == 1
    assert "уже установлен" in result["errors"][0]["error"]


def test_bulk_disable_route_on_unpublished_is_truthful_failure(db_session, draft_place_factory) -> None:
    place = draft_place_factory(slug="bulk-route-draft")
    result = apply_bulk(
        db_session,
        [place.id],
        "disable_route",
        {"reason": "not applicable"},
        actor="test-admin",
    )
    assert result["applied"] == 0
    assert result["failed"] == 1
    assert "только у опубликованного" in result["errors"][0]["error"]


def test_bulk_verify_sets_full_verification_contract(db_session, draft_place_factory) -> None:
    place = draft_place_factory(slug="bulk-verify-full")
    place.verification_status = "unverified"
    place.existence_confidence_level = "unknown"
    place.existence_confidence_score = 0
    db_session.commit()

    result = apply_bulk(db_session, [place.id], "verify", {}, actor="test-admin")
    assert result == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.verification_status == "verified"
    assert place.existence_confidence_level == "high"
    assert place.existence_confidence_score >= 90
    assert place.verified_by == "test-admin"
    assert place.verified_at is not None
