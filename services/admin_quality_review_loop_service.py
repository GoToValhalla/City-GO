from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class QualityReviewLoopError(ValueError):
    pass


REVIEW_LOOP_ITEM_KINDS: tuple[str, ...] = (
    "place_change",
    "data_quality_issue",
    "duplicate_candidate",
    "conflict_candidate",
    "photo_candidate",
)

QUALITY_REVIEW_ACTIONS: tuple[str, ...] = ("approve", "reject", "defer")
OPEN_REVIEW_STATUSES: set[str] = {"open", "pending", "candidate", "needs_review"}
DEFERRED_REVIEW_STATUS = "deferred"
TERMINAL_REVIEW_STATUSES: set[str] = {"resolved", "approved", "rejected", "applied", "dismissed", "skipped"}
PUBLICATION_BLOCKING_ISSUE_TYPES: tuple[str, ...] = (
    "duplicate_candidate",
    "conflict_candidate",
    "route_eligibility_suspicious",
    "missing_primary_photo",
    "missing_address",
    "missing_coordinates",
    "weak_description",
)
DUPLICATE_CONFLICT_REVIEW_TYPES: tuple[str, ...] = ("duplicate_candidate", "conflict_candidate")
PHOTO_REVIEW_TYPES: tuple[str, ...] = ("photo_candidate", "missing_primary_photo")


@dataclass(frozen=True)
class ReviewActionState:
    action: str
    previous_status: str
    next_status: str
    resolution: str
    is_terminal: bool
    button_enabled_after_action: bool


def normalize_review_status(status: str | None) -> str:
    return (status or "").strip().lower()


def normalize_review_action(action: str | None) -> str:
    return (action or "").strip().lower()


def assert_review_action_allowed(*, status: str, action: str) -> None:
    normalized_status = normalize_review_status(status)
    normalized_action = normalize_review_action(action)
    if normalized_action not in QUALITY_REVIEW_ACTIONS:
        raise QualityReviewLoopError(f"Unsupported quality review action: {action}")
    if normalized_status in TERMINAL_REVIEW_STATUSES:
        raise QualityReviewLoopError(f"Quality review item is already completed: {status}")
    if normalized_status == DEFERRED_REVIEW_STATUS and normalized_action == "defer":
        raise QualityReviewLoopError("Quality review item is already deferred")
    if normalized_status not in OPEN_REVIEW_STATUSES and normalized_status != DEFERRED_REVIEW_STATUS:
        raise QualityReviewLoopError(f"Quality review item is not actionable: {status}")


def resolve_review_action_state(*, status: str, action: str, item_kind: str = "place_change") -> ReviewActionState:
    assert_review_action_allowed(status=status, action=action)
    normalized_status = normalize_review_status(status)
    normalized_action = normalize_review_action(action)
    normalized_kind = (item_kind or "place_change").strip().lower()
    if normalized_action == "defer":
        return ReviewActionState(normalized_action, normalized_status, DEFERRED_REVIEW_STATUS, "deferred", False, False)
    if normalized_kind in PHOTO_REVIEW_TYPES:
        next_status = "approved" if normalized_action == "approve" else "rejected"
    else:
        next_status = "resolved"
    return ReviewActionState(
        normalized_action,
        normalized_status,
        next_status,
        "approved" if normalized_action == "approve" else "rejected",
        True,
        False,
    )


def build_candidate_evidence_view(
    *,
    item_kind: str,
    item_id: int,
    place_id: int | None,
    evidence: Mapping[str, object] | None,
    proposed_patch: Mapping[str, object] | None = None,
) -> dict[str, object]:
    normalized_kind = (item_kind or "").strip().lower()
    if normalized_kind not in REVIEW_LOOP_ITEM_KINDS:
        raise QualityReviewLoopError(f"Unsupported quality review item kind: {item_kind}")
    evidence_payload = dict(evidence or {})
    patch_payload = dict(proposed_patch or {})
    missing_evidence = [key for key in ("source", "reason", "confidence") if evidence_payload.get(key) in (None, "", [])]
    return {
        "item_kind": normalized_kind,
        "item_id": item_id,
        "place_id": place_id,
        "evidence": evidence_payload,
        "proposed_patch": patch_payload,
        "has_evidence": not missing_evidence,
        "missing_evidence": missing_evidence,
        "requires_merge_safety_review": normalized_kind in DUPLICATE_CONFLICT_REVIEW_TYPES,
        "requires_photo_review": normalized_kind in PHOTO_REVIEW_TYPES,
    }


def build_quality_dashboard_v2(
    *,
    open_review_count: int,
    blocking_issue_counts: Mapping[str, int] | None = None,
    duplicate_candidate_count: int = 0,
    conflict_candidate_count: int = 0,
    photo_candidate_count: int = 0,
) -> dict[str, object]:
    issue_counts = {issue_type: max(0, int(count)) for issue_type, count in dict(blocking_issue_counts or {}).items()}
    blockers: list[dict[str, object]] = []
    for issue_type in PUBLICATION_BLOCKING_ISSUE_TYPES:
        count = issue_counts.get(issue_type, 0)
        if count > 0:
            blockers.append({"type": issue_type, "count": count})
    for blocker_type, count in (
        ("duplicate_candidate", duplicate_candidate_count),
        ("conflict_candidate", conflict_candidate_count),
        ("photo_candidate", photo_candidate_count),
    ):
        if count > 0:
            blockers.append({"type": blocker_type, "count": int(count)})
    total_blockers = sum(int(blocker["count"]) for blocker in blockers)
    normalized_open_review_count = max(0, int(open_review_count))
    return {
        "open_review_count": normalized_open_review_count,
        "total_blockers": total_blockers,
        "blocks_publication": total_blockers > 0 or normalized_open_review_count > 0,
        "blockers": blockers,
        "next_actions": _dashboard_next_actions(
            open_review_count=normalized_open_review_count,
            duplicate_candidate_count=duplicate_candidate_count,
            conflict_candidate_count=conflict_candidate_count,
            photo_candidate_count=photo_candidate_count,
        ),
    }


def build_review_queue_page(*, items: Sequence[Mapping[str, object]], total: int, limit: int, offset: int) -> dict[str, object]:
    if limit < 1 or limit > 100:
        raise QualityReviewLoopError("Review queue limit must be between 1 and 100")
    if offset < 0:
        raise QualityReviewLoopError("Review queue offset must be non-negative")
    normalized_total = max(0, int(total))
    normalized_items = [dict(item) for item in items]
    next_offset = offset + len(normalized_items)
    return {
        "items": normalized_items,
        "total": normalized_total,
        "limit": limit,
        "offset": offset,
        "has_next": next_offset < normalized_total,
        "next_offset": next_offset if next_offset < normalized_total else None,
        "sort": ["created_at", "id"],
    }


def assert_review_queue_filters_supported(filters: Mapping[str, object]) -> None:
    allowed_filters = {"city_slug", "category", "status", "severity", "item_kind", "route_eligible", "has_photo"}
    unsupported = sorted(set(filters) - allowed_filters)
    if unsupported:
        raise QualityReviewLoopError(f"Unsupported review queue filters: {unsupported}")


def _dashboard_next_actions(
    *,
    open_review_count: int,
    duplicate_candidate_count: int,
    conflict_candidate_count: int,
    photo_candidate_count: int,
) -> list[str]:
    actions: list[str] = []
    if open_review_count > 0:
        actions.append("review_open_items")
    if duplicate_candidate_count > 0:
        actions.append("resolve_duplicates")
    if conflict_candidate_count > 0:
        actions.append("resolve_conflicts")
    if photo_candidate_count > 0:
        actions.append("review_photo_candidates")
    return actions
