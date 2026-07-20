from __future__ import annotations

from models.taxonomy import QualityIssue, QualityRule
from services.taxonomy_automation_service import validate_place


def test_validation_closes_issue_when_failure_is_fixed(db_session, draft_place_factory) -> None:
    place = draft_place_factory(
        slug="quality-issue-lifecycle",
        address=None,
    )
    place.short_description = (
        "Описание достаточной длины для проверки жизненного цикла quality issue. " * 2
    )
    db_session.flush()

    validate_place(db_session, place)
    db_session.flush()

    rule = db_session.query(QualityRule).filter(QualityRule.code == "address_required").one()
    issue = db_session.query(QualityIssue).filter(
        QualityIssue.place_id == place.id,
        QualityIssue.rule_id == rule.id,
    ).one()
    assert issue.status == "open"
    assert issue.fixed_at is None

    place.address = "Тестовый адрес, 1"
    validate_place(db_session, place)
    db_session.flush()
    db_session.refresh(issue)

    assert issue.status == "fixed"
    assert issue.fixed_at is not None
