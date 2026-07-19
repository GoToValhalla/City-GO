from __future__ import annotations

import pytest

from core.publication_state_ownership import CONTROLLED_PLACE_INPUT_FIELDS
from models.place_publication_transition import PlacePublicationTransition
from services.admin_place_bulk_service import apply_bulk
from services.admin_place_update_service import _ALLOWED, _CONTROLLED_FIELDS, update_admin_place_fields


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("publication_status", "hidden"),
        ("is_published", False),
        ("is_visible_in_catalog", False),
        ("is_searchable", False),
        ("is_route_eligible", False),
        ("route_exclusion_reason", "bypass"),
        ("verification_status", "verified"),
        ("verified_by", "bypass"),
        ("verified_at", None),
        ("existence_confidence_level", "high"),
        ("visible_to_users", False),
        ("route_enabled", False),
    ],
)
def test_generic_admin_update_rejects_all_controlled_state(
    db_session, published_place_factory, field: str, value: object
) -> None:
    place = published_place_factory(slug=f"controlled-boundary-{field.replace('_', '-')}")
    before = (
        place.publication_status,
        place.is_published,
        place.is_route_eligible,
        place.route_exclusion_reason,
        place.verification_status,
        place.verified_by,
    )
    with pytest.raises(ValueError, match="Управляемые поля состояния"):
        update_admin_place_fields(db_session, place.id, {field: value}, actor="test-admin")
    db_session.refresh(place)
    assert (
        place.publication_status,
        place.is_published,
        place.is_route_eligible,
        place.route_exclusion_reason,
        place.verification_status,
        place.verified_by,
    ) == before


def test_generic_admin_allowlist_is_disjoint_from_all_controlled_state() -> None:
    assert _CONTROLLED_FIELDS == CONTROLLED_PLACE_INPUT_FIELDS
    assert _ALLOWED.isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)


def test_bulk_category_update_reconciles_excluded_category(db_session, published_place_factory) -> None:
    place = published_place_factory(slug="bulk-category-excluded", category="museum")
    result = apply_bulk(
        db_session, [place.id], "set_category", {"category": "transport"}, actor="test-admin"
    )
    assert result == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.category == "transport"
    assert place.publication_status == "needs_review"
    assert place.is_published is False
    assert place.is_route_eligible is False
    assert place.publication_reason_code == "non_public_category"


def test_bulk_route_writer_keeps_flag_and_reason_consistent(db_session, published_place_factory) -> None:
    place = published_place_factory(slug="bulk-route-writer", category="museum")
    initial_count = db_session.query(PlacePublicationTransition).filter(
        PlacePublicationTransition.place_id == place.id
    ).count()
    disabled = apply_bulk(
        db_session,
        [place.id],
        "disable_route",
        {"reason": "Временно исключено"},
        actor="test-admin",
    )
    assert disabled == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.is_route_eligible is False
    assert place.route_exclusion_reason == "Временно исключено"

    enabled = apply_bulk(
        db_session,
        [place.id],
        "enable_route",
        {"reason": "Возвращено"},
        actor="test-admin",
    )
    assert enabled == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.is_route_eligible is True
    assert place.route_exclusion_reason is None
    assert db_session.query(PlacePublicationTransition).filter(
        PlacePublicationTransition.place_id == place.id
    ).count() == initial_count + 2


def test_bulk_verify_sets_full_contract(db_session, draft_place_factory) -> None:
    place = draft_place_factory(slug="bulk-verify-full")
    result = apply_bulk(db_session, [place.id], "verify", {}, actor="test-admin")
    assert result == {"applied": 1, "failed": 0, "errors": []}
    db_session.refresh(place)
    assert place.verification_status == "verified"
    assert place.existence_confidence_level == "high"
    assert place.existence_confidence_score >= 90
    assert place.verified_by == "test-admin"
    assert place.verified_at is not None


def test_bulk_noop_is_truthful_failure(db_session, published_place_factory) -> None:
    place = published_place_factory(slug="bulk-route-noop", category="museum")
    result = apply_bulk(
        db_session, [place.id], "enable_route", {"reason": "already enabled"}, actor="test-admin"
    )
    assert result["applied"] == 0
    assert result["failed"] == 1
