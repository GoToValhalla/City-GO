from __future__ import annotations

from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.candidate_retrieval_service import CandidateRetrievalService


def _ctx() -> MergedContext:
    return MergedContext(
        location=(43.10, 76.80),
        city_id="almaty",
        timezone="Asia/Almaty",
        time_budget_minutes=240,
        effective_time_budget_minutes=240,
        time_of_day=None,
        route_time_mode="flexible",
        interests=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=1000,
        effective_num_stops=6,
        min_stop_duration_minutes=20,
    )


def _place(place_id: int, lat: float, lng: float, category: str = "museum") -> SimpleNamespace:
    return SimpleNamespace(
        id=place_id,
        title=f"Place {place_id}",
        lat=lat,
        lng=lng,
        category=category,
        address="Center",
        short_description="A route candidate",
        opening_hours={"mon": {"open": "10:00", "close": "18:00"}},
        quality_score=80,
    )


class IsolatedStartRetrieval(CandidateRetrievalService):
    def _safe_spatial_density(self, db: object, ctx: MergedContext) -> dict[str, int | None]:
        return {
            "places_within_500m": 0,
            "places_within_1km": 0,
            "places_within_2km": 0,
            "places_within_5km": 0,
            "places_within_10km": 0,
            "city_wide_eligible": 215,
        }

    def _safe_retrieval_counts(self, db: object, ctx: MergedContext) -> dict[str, object]:
        return {
            "city_scope_total": 215,
            "route_eligible_before_user_exclusions": 215,
            "route_eligible_after_user_exclusions": 215,
            "radius_before_user_exclusions": 0,
            "radius_after_user_exclusions": 0,
            "expanded_radius_before_user_exclusions": 0,
            "expanded_radius_after_user_exclusions": 0,
            "city_wide_after_user_exclusions": 215,
            "lost_by_user_exclusions_city_wide": 0,
            "lost_by_user_exclusions_radius": 0,
        }

    def _query_places(self, db: object, ctx: MergedContext) -> list[SimpleNamespace]:
        return []

    def _fallback_expand_radius(self, db: object, ctx: MergedContext) -> list[SimpleNamespace]:
        return []

    def _fallback_city_wide(self, db: object, ctx: MergedContext) -> list[SimpleNamespace]:
        return [_place(1, 43.238, 76.945), _place(2, 43.24, 76.95, "park")]

    def _safe_attach_public_images(self, db: object, candidates: list[SimpleNamespace]) -> list[SimpleNamespace]:
        return candidates


def test_isolated_start_uses_city_wide_nearest_fallback_new() -> None:
    service = IsolatedStartRetrieval()

    candidates = service.get_candidates(object(), _ctx())

    assert [candidate.id for candidate in candidates] == [1, 2]
    assert service.last_debug["raw_candidates_count"] == 0
    assert service.last_debug["final_candidates_count"] == 2
    assert service.last_debug["fallback_radius_used"] is True
    assert service.last_debug["fallback_city_wide_used"] is True
    assert service.last_debug["retrieval_strategy_used"] == "city_wide_fallback"
    assert service.last_debug["retrieval_loss_summary"]["lost_before_radius"] == 215
