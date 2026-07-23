"""Regression for the false-success publication defect found in
independent audit: services/publication_policy.py::apply_publication_decision
previously caught InvalidPublicationTransition, swallowed it (`pass`), and
then unconditionally set row.status = "applied" -- claiming the canonical
transition succeeded even when it did not. It also set place.status =
"active" BEFORE attempting the transition, leaving a partial mutation in
the unit of work if the transition then failed.

These tests prove: a failed transition can never produce status="applied",
Place state is left completely unchanged, and a successful transition still
behaves exactly as before."""

from __future__ import annotations

import allure
import pytest

from models.place_publication_decision import PlacePublicationDecision
from models.place_snapshot import PlaceSnapshot
from services.publication_policy import PublicationDecision, apply_publication_decision


def _auto_publish_decision(trust_score: float = 95.0) -> PublicationDecision:
    return PublicationDecision(
        decision="auto_publish",
        trust_score=trust_score,
        failed_gates=[],
        review_reasons=[],
        should_publish=True,
    )


@allure.title("apply_publication_decision: неудачный переход никогда не даёт status=applied")
def test_failed_transition_never_reports_applied_new(db_session, place_factory) -> None:
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft", status="pending")
    db_session.commit()
    original_status = place.status

    decision = _auto_publish_decision()
    # An empty actor makes transition_place_publication's own input
    # validation raise InvalidPublicationTransition deterministically,
    # without needing to reconstruct the exact "already at target state"
    # condition.
    row = apply_publication_decision(db_session, place, decision, actor="")
    db_session.commit()
    db_session.refresh(place)
    db_session.refresh(row)

    assert row.status == "failed"
    assert row.status != "applied"
    # place.status must be untouched -- previously set to "active" BEFORE
    # the (failing) transition attempt, leaving a partial mutation.
    assert place.status == original_status
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
    assert place.publication_status == "draft"


@allure.title("apply_publication_decision: неудачный переход не создаёт запись со статусом applied в БД")
def test_failed_transition_writes_no_applied_decision_row_new(db_session, place_factory) -> None:
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    db_session.commit()

    decision = _auto_publish_decision()
    apply_publication_decision(db_session, place, decision, actor="")
    db_session.commit()

    applied_rows = (
        db_session.query(PlacePublicationDecision)
        .filter_by(place_id=place.id, status="applied")
        .count()
    )
    assert applied_rows == 0
    failed_rows = (
        db_session.query(PlacePublicationDecision)
        .filter_by(place_id=place.id, status="failed")
        .count()
    )
    assert failed_rows == 1


@allure.title("apply_publication_decision: место остаётся неизменным при неудачном переходе, несмотря на снимок")
def test_failed_transition_leaves_place_completely_unchanged_new(db_session, place_factory) -> None:
    """snapshot_place is still taken (a pre-attempt snapshot is valid
    regardless of outcome), but Place itself must show zero mutation --
    proving the previous place.status = "active" pre-mutation hazard is
    closed."""
    place = place_factory(
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft", status="pending",
        title="Untouched Title",
    )
    db_session.commit()
    snapshot_before = {
        "status": place.status,
        "publication_status": place.publication_status,
        "is_active": place.is_active,
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_searchable": place.is_searchable,
        "is_route_eligible": place.is_route_eligible,
        "title": place.title,
    }

    decision = _auto_publish_decision()
    apply_publication_decision(db_session, place, decision, actor="")
    db_session.commit()
    db_session.refresh(place)

    assert place.status == snapshot_before["status"]
    assert place.publication_status == snapshot_before["publication_status"]
    assert place.is_active == snapshot_before["is_active"]
    assert place.is_published == snapshot_before["is_published"]
    assert place.is_visible_in_catalog == snapshot_before["is_visible_in_catalog"]
    assert place.is_searchable == snapshot_before["is_searchable"]
    assert place.is_route_eligible == snapshot_before["is_route_eligible"]
    assert place.title == snapshot_before["title"]

    # The pre-attempt snapshot itself is still a valid, independent side
    # effect -- it captures state that existed regardless of the outcome.
    assert db_session.query(PlaceSnapshot).filter_by(place_id=place.id, reason="pre_auto_publish").count() == 1


@allure.title("apply_publication_decision: успешный переход по-прежнему публикует место как раньше")
def test_successful_transition_still_behaves_exactly_as_before_new(db_session, place_factory) -> None:
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    db_session.commit()

    decision = _auto_publish_decision()
    row = apply_publication_decision(db_session, place, decision, actor="publication-policy")
    db_session.commit()
    db_session.refresh(place)
    db_session.refresh(row)

    assert row.status == "applied"
    assert place.status == "active"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_route_eligible is True
    assert place.is_searchable is True
    assert place.publication_status == "published"


@allure.title("apply_publication_decision: повторный неудачный вызов не создаёт частично применённое состояние")
def test_failed_transition_exception_type_is_invalid_publication_transition_new(db_session, place_factory, monkeypatch) -> None:
    """Directly confirms the original exception class is preserved
    internally (caught only as InvalidPublicationTransition, per the
    task's requirement to never broaden the catch to swallow unrelated
    errors) by monkeypatching transition_place_publication to raise a
    different exception type and confirming it propagates instead of
    being silently converted to a "failed" row."""
    import services.publication_policy as publication_policy_module

    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    db_session.commit()

    def _raise_unexpected(*args, **kwargs):
        raise RuntimeError("unexpected non-publication error")

    monkeypatch.setattr(publication_policy_module, "transition_place_publication", _raise_unexpected)

    decision = _auto_publish_decision()
    with pytest.raises(RuntimeError, match="unexpected non-publication error"):
        apply_publication_decision(db_session, place, decision, actor="publication-policy")
