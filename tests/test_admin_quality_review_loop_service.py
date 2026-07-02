from __future__ import annotations

import pytest

from services.admin_quality_review_loop_service import (
    QualityReviewLoopError,
    assert_review_action_allowed,
    assert_review_queue_filters_supported,
    build_candidate_evidence_view,
    build_quality_dashboard_v2,
    build_review_queue_page,
    resolve_review_action_state,
)
from tests.allure_support import title


@title("Quality dashboard v2 показывает блокеры публикации и следующие действия")
def test_quality_dashboard_v2_exposes_publication_blockers_and_next_actions() -> None:
    dashboard = build_quality_dashboard_v2(
        open_review_count=4,
        blocking_issue_counts={
            "missing_address": 3,
            "weak_description": 2,
            "non_blocking_note": 99,
        },
        duplicate_candidate_count=1,
        conflict_candidate_count=2,
        photo_candidate_count=5,
    )

    assert dashboard["blocks_publication"] is True
    assert dashboard["open_review_count"] == 4
    assert dashboard["total_blockers"] == 13
    assert dashboard["blockers"] == [
        {"type": "missing_address", "count": 3},
        {"type": "weak_description", "count": 2},
        {"type": "duplicate_candidate", "count": 1},
        {"type": "conflict_candidate", "count": 2},
        {"type": "photo_candidate", "count": 5},
    ]
    assert dashboard["next_actions"] == [
        "review_open_items",
        "resolve_duplicates",
        "resolve_conflicts",
        "review_photo_candidates",
    ]


@title("Quality dashboard v2 не блокирует публикацию без открытых review и блокеров")
def test_quality_dashboard_v2_allows_publication_when_queue_is_clean() -> None:
    dashboard = build_quality_dashboard_v2(open_review_count=0)

    assert dashboard["blocks_publication"] is False
    assert dashboard["total_blockers"] == 0
    assert dashboard["blockers"] == []
    assert dashboard["next_actions"] == []


@title("Review loop разрешает approve reject defer только для action-ready items")
def test_review_loop_allows_actions_only_for_actionable_items() -> None:
    assert_review_action_allowed(status="open", action="approve")
    assert_review_action_allowed(status="pending", action="reject")
    assert_review_action_allowed(status="candidate", action="defer")
    assert_review_action_allowed(status="deferred", action="approve")

    with pytest.raises(QualityReviewLoopError):
        assert_review_action_allowed(status="resolved", action="approve")

    with pytest.raises(QualityReviewLoopError):
        assert_review_action_allowed(status="approved", action="reject")

    with pytest.raises(QualityReviewLoopError):
        assert_review_action_allowed(status="deferred", action="defer")

    with pytest.raises(QualityReviewLoopError):
        assert_review_action_allowed(status="open", action="merge")


@title("Review loop после действия выключает повторную кнопку")
def test_review_action_state_disables_button_after_action() -> None:
    approved = resolve_review_action_state(status="open", action="approve")
    rejected = resolve_review_action_state(status="open", action="reject")
    deferred = resolve_review_action_state(status="open", action="defer")

    assert approved.next_status == "resolved"
    assert approved.resolution == "approved"
    assert approved.is_terminal is True
    assert approved.button_enabled_after_action is False

    assert rejected.next_status == "resolved"
    assert rejected.resolution == "rejected"
    assert rejected.is_terminal is True
    assert rejected.button_enabled_after_action is False

    assert deferred.next_status == "deferred"
    assert deferred.resolution == "deferred"
    assert deferred.is_terminal is False
    assert deferred.button_enabled_after_action is False


@title("Photo candidate approval использует photo status lifecycle")
def test_photo_candidate_approval_uses_photo_status_lifecycle() -> None:
    approved = resolve_review_action_state(status="candidate", action="approve", item_kind="photo_candidate")
    rejected = resolve_review_action_state(status="candidate", action="reject", item_kind="photo_candidate")

    assert approved.next_status == "approved"
    assert approved.resolution == "approved"
    assert approved.button_enabled_after_action is False
    assert rejected.next_status == "rejected"
    assert rejected.resolution == "rejected"
    assert rejected.button_enabled_after_action is False


@title("Candidate evidence view показывает provenance и missing evidence")
def test_candidate_evidence_view_exposes_provenance_and_missing_evidence() -> None:
    view = build_candidate_evidence_view(
        item_kind="duplicate_candidate",
        item_id=11,
        place_id=42,
        evidence={"source": "deterministic", "reason": "same_name_same_address", "confidence": 0.96},
        proposed_patch={"merge_into_place_id": 41},
    )

    assert view["has_evidence"] is True
    assert view["missing_evidence"] == []
    assert view["requires_merge_safety_review"] is True
    assert view["requires_photo_review"] is False
    assert view["proposed_patch"] == {"merge_into_place_id": 41}

    incomplete = build_candidate_evidence_view(
        item_kind="photo_candidate",
        item_id=12,
        place_id=43,
        evidence={"source": "provider"},
    )

    assert incomplete["has_evidence"] is False
    assert incomplete["missing_evidence"] == ["reason", "confidence"]
    assert incomplete["requires_photo_review"] is True

    with pytest.raises(QualityReviewLoopError):
        build_candidate_evidence_view(item_kind="unknown", item_id=13, place_id=None, evidence={})


@title("Review queue page стабильно пагинируется и возвращает следующий offset")
def test_review_queue_page_is_stably_paginated() -> None:
    page = build_review_queue_page(
        items=[{"id": 1, "created_at": "2026-07-02T10:00:00"}, {"id": 2, "created_at": "2026-07-02T10:01:00"}],
        total=5,
        limit=2,
        offset=0,
    )

    assert page["items"] == [
        {"id": 1, "created_at": "2026-07-02T10:00:00"},
        {"id": 2, "created_at": "2026-07-02T10:01:00"},
    ]
    assert page["has_next"] is True
    assert page["next_offset"] == 2
    assert page["sort"] == ["created_at", "id"]

    last_page = build_review_queue_page(items=[{"id": 5}], total=5, limit=2, offset=4)
    assert last_page["has_next"] is False
    assert last_page["next_offset"] is None

    with pytest.raises(QualityReviewLoopError):
        build_review_queue_page(items=[], total=0, limit=0, offset=0)

    with pytest.raises(QualityReviewLoopError):
        build_review_queue_page(items=[], total=0, limit=101, offset=0)

    with pytest.raises(QualityReviewLoopError):
        build_review_queue_page(items=[], total=0, limit=50, offset=-1)


@title("Review queue v2 поддерживает только явные фильтры")
def test_review_queue_filters_are_explicitly_supported() -> None:
    assert_review_queue_filters_supported(
        {
            "city_slug": "almaty",
            "category": "museum",
            "status": "open",
            "severity": "high",
            "item_kind": "duplicate_candidate",
            "route_eligible": True,
            "has_photo": False,
        }
    )

    with pytest.raises(QualityReviewLoopError):
        assert_review_queue_filters_supported({"free_text_magic": "anything"})
