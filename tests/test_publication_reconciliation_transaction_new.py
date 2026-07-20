from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.admin_place_bulk_service import apply_bulk
from services.admin_place_update_service import update_admin_place_fields
from services.place_publication_reconciliation import reconcile_published_place


def test_single_category_workflow_failure_rolls_back_all_changes(
    db_session,
    published_place_factory,
    monkeypatch,
) -> None:
    place = published_place_factory(slug="category-workflow-rollback-single", category="museum")
    original_category_id = place.category_id

    monkeypatch.setattr(
        "services.admin_place_update_service.run_workflow",
        lambda *args, **kwargs: SimpleNamespace(status="failed", error_message="workflow failed"),
    )

    nested = db_session.begin_nested()
    with pytest.raises(ValueError, match="workflow failed"):
        update_admin_place_fields(
            db_session,
            place.id,
            {"category": "transport"},
            actor="test-admin",
            commit=False,
        )
    nested.rollback()

    db_session.refresh(place)
    assert place.category == "museum"
    assert place.category_id == original_category_id
    assert place.publication_status == "published"
    assert place.is_published is True


def test_bulk_category_workflow_failure_is_per_row_failure_and_rolls_back(
    db_session,
    published_place_factory,
    monkeypatch,
) -> None:
    place = published_place_factory(slug="category-workflow-rollback-bulk", category="museum")

    monkeypatch.setattr(
        "services.admin_place_update_service.run_workflow",
        lambda *args, **kwargs: SimpleNamespace(status="failed", error_message="workflow failed"),
    )

    result = apply_bulk(
        db_session,
        [place.id],
        "set_category",
        {"category": "transport"},
        actor="test-admin",
    )

    assert result["applied"] == 0
    assert result["failed"] == 1
    assert "workflow failed" in result["errors"][0]["error"]
    db_session.refresh(place)
    assert place.category == "museum"
    assert place.publication_status == "published"
    assert place.is_published is True


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        # places.lat is NOT NULL; missing coordinates is covered by eligibility unit tests.
        (lambda place: setattr(place, "is_duplicate_suspected", True), "duplicate_suspected"),
        (lambda place: setattr(place, "is_spam_poi", True), "spam_suspected"),
        (lambda place: setattr(place, "category", "transport"), "non_public_category"),
    ],
)
def test_reconciliation_uses_truthful_primary_reason(
    db_session,
    published_place_factory,
    mutator,
    expected_reason: str,
) -> None:
    place = published_place_factory(slug=f"reconcile-{expected_reason}", category="museum")
    mutator(place)

    outcome = reconcile_published_place(
        db_session,
        place,
        actor="test-admin",
        source="test_reconciliation",
        reason="metadata changed",
        lock_place=False,
    )
    db_session.commit()
    db_session.refresh(place)

    assert outcome == "moved_to_review"
    assert place.publication_status == "needs_review"
    assert place.publication_reason_code == expected_reason
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
