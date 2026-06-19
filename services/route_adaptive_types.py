from __future__ import annotations

from dataclasses import dataclass

from services.scoring_service import ScoredPlace


@dataclass(frozen=True)
class RoutePlan:
    scored: list[ScoredPlace]
    target_points: int
    exact_count: int
    related_count: int
    neutral_count: int
    expansion_level: str
    expanded_category_count: int
    neutral_added_count: int
    warnings: list[str]
    user_explanation: str

    @property
    def expanded_pool_count(self) -> int:
        return len(self.scored)
