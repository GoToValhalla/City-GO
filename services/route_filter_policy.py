from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from schemas.merged_context import MergedContext
from services.route_filter_reasons import OpenState, budget_reason, hard_reason, place_id

DROP_BY_STATUS = "dropped_by_status"
DROP_BY_EXCLUSION = "dropped_by_exclusion"
DROP_BY_TIME = "dropped_by_time"

_STATUS_REASONS = frozenset({"status"})
_EXCLUSION_REASONS = frozenset({"explicit_place_exclude", "avoided_category"})
_TIME_REASONS = frozenset({"closed_now", "unknown_hours_time_sensitive"})


@dataclass(frozen=True)
class FilterDecision:
    place_id: str
    reason: str


@dataclass(frozen=True)
class FilterReport:
    kept: list[object]
    rejected: tuple[FilterDecision, ...]
    fallback_used: bool
    strict_kept_count: int
    relaxed_kept_count: int
    strict_rejected: tuple[FilterDecision, ...]
    relaxed_rejected: tuple[FilterDecision, ...]

    @property
    def reason_counts(self) -> dict[str, int]:
        return _reason_counts(self.rejected)

    @property
    def strict_reason_counts(self) -> dict[str, int]:
        return _reason_counts(self.strict_rejected)

    @property
    def relaxed_reason_counts(self) -> dict[str, int]:
        return _reason_counts(self.relaxed_rejected)


def filter_places(
    places: list[object],
    ctx: MergedContext,
    now: datetime,
    min_pool_size: int,
    open_state: OpenState,
) -> FilterReport:
    strict = tuple((place_id(place), _strict_reason(place, ctx, now, open_state)) for place in places)
    strict_kept = [place for place, item in zip(places, strict) if item[1] is None]
    strict_rejected = _rejected(strict)
    if len(strict_kept) >= min_pool_size:
        return FilterReport(strict_kept, strict_rejected, False, len(strict_kept), len(strict_kept), strict_rejected, strict_rejected)
    relaxed = tuple((place_id(place), hard_reason(place, ctx, now, open_state)) for place in places)
    relaxed_kept = [place for place, item in zip(places, relaxed) if item[1] is None]
    relaxed_rejected = _rejected(relaxed)
    return FilterReport(relaxed_kept, relaxed_rejected, True, len(strict_kept), len(relaxed_kept), strict_rejected, relaxed_rejected)


def _rejected(items: tuple[tuple[str, str | None], ...]) -> tuple[FilterDecision, ...]:
    return tuple(FilterDecision(place_id, reason) for place_id, reason in items if reason is not None)


def _reason_counts(items: tuple[FilterDecision, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.reason] = counts.get(item.reason, 0) + 1
        bucket = _diagnostic_bucket(item.reason)
        if bucket:
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _diagnostic_bucket(reason: str) -> str | None:
    if reason in _STATUS_REASONS:
        return DROP_BY_STATUS
    if reason in _EXCLUSION_REASONS:
        return DROP_BY_EXCLUSION
    if reason in _TIME_REASONS:
        return DROP_BY_TIME
    return None


def _strict_reason(place: object, ctx: MergedContext, now: datetime, open_state: OpenState) -> str | None:
    return hard_reason(place, ctx, now, open_state) or budget_reason(place, ctx)