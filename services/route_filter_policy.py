from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from schemas.merged_context import MergedContext
from services.route_filter_reasons import OpenState, budget_reason, hard_reason, place_id


@dataclass(frozen=True)
class FilterDecision:
    place_id: str
    reason: str


@dataclass(frozen=True)
class FilterReport:
    kept: list[object]
    rejected: tuple[FilterDecision, ...]
    fallback_used: bool

    @property
    def reason_counts(self) -> dict[str, int]:
        return {reason: sum(item.reason == reason for item in self.rejected)
                for reason in {item.reason for item in self.rejected}}


def filter_places(
    places: list[object],
    ctx: MergedContext,
    now: datetime,
    min_pool_size: int,
    open_state: OpenState,
) -> FilterReport:
    strict = tuple((place_id(place), _strict_reason(place, ctx, now, open_state)) for place in places)
    strict_kept = [place for place, item in zip(places, strict) if item[1] is None]
    if len(strict_kept) >= min_pool_size:
        return FilterReport(strict_kept, _rejected(strict), False)
    relaxed = tuple((place_id(place), hard_reason(place, ctx, now, open_state)) for place in places)
    relaxed_kept = [place for place, item in zip(places, relaxed) if item[1] is None]
    return FilterReport(relaxed_kept, _rejected(relaxed), True)


def _rejected(items: tuple[tuple[str, str | None], ...]) -> tuple[FilterDecision, ...]:
    return tuple(FilterDecision(place_id, reason) for place_id, reason in items if reason is not None)


def _strict_reason(place: object, ctx: MergedContext, now: datetime, open_state: OpenState) -> str | None:
    return hard_reason(place, ctx, now, open_state) or budget_reason(place, ctx)
