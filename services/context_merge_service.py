"""
Сборка MergedContext из HTTP/бот-запроса и опционального UserProfile (без обращений к БД).
"""
from typing import Optional, List

from schemas.merged_context import (
    MergedContext,
    BudgetLevel,
    PaceMode,
    compute_radius,
    compute_effective_time_budget,
    compute_num_stops,
    compute_min_stop_duration,
    mood_to_pace,
)

from schemas.user_profile import UserProfile


# -----------------------------
# INPUT MODELS (минимальные) — входные модели без привязки к Pydantic-схеме HTTP.
# -----------------------------

class RequestContext:
    """
    Упрощённый перенос данных запроса (аналог DTO); позже можно заменить на явную Pydantic-схему.
    """

    def __init__(
        self,
        location: Optional[tuple[float, float]] = None,
        city_id: Optional[str] = None,
        timezone: Optional[str] = None,
        time_budget_minutes: Optional[int] = None,
        time_of_day: Optional[str] = None,
        route_time_mode: Optional[str] = None,
        interests: Optional[List[str]] = None,
        avoided_categories: Optional[List[str]] = None,
        excluded_place_ids: Optional[List[str]] = None,
        budget_level: Optional[int] = None,
        pace_mode: Optional[str] = None,
        is_visiting: Optional[bool] = None,
        visit_city_id: Optional[str] = None,
        visit_days: Optional[int] = None,
        start_source: Optional[str] = None,
        start_warnings: Optional[List[str]] = None,
        is_admin: Optional[bool] = None,
    ):
        self.location = location
        self.city_id = city_id
        self.timezone = timezone or "UTC"
        self.time_budget_minutes = time_budget_minutes
        self.time_of_day = time_of_day
        self.route_time_mode = route_time_mode or "flexible"
        self.interests = interests or []
        self.avoided_categories = avoided_categories or []
        self.excluded_place_ids = excluded_place_ids or []
        self.budget_level = budget_level
        self.pace_mode = pace_mode
        self.is_visiting = is_visiting
        self.visit_city_id = visit_city_id
        self.visit_days = visit_days
        self.start_source = start_source or "city_center"
        self.start_warnings = list(start_warnings or [])
        self.is_admin = bool(is_admin)


# -----------------------------
# SERVICE — класс сервиса слияния контекста.
# -----------------------------

class ContextMergeService:
    """
    Главный сервис, который собирает merged_context.

    ВАЖНО:
    - никаких запросов к БД здесь
    - только объединение входных данных
    - чистая логика → легко тестируется
    """

    DEFAULT_TIME_BUDGET = 120
    DEFAULT_BUDGET = BudgetLevel.MID
    DEFAULT_PACE = PaceMode.NORMAL

    def merge(
        self,
        request: RequestContext,
        profile: Optional[UserProfile] = None,
    ) -> MergedContext:

        location = self._resolve_location(request, profile)

        time_budget = (
            request.time_budget_minutes
            or (profile.behavior.preferred_time_budget_minutes if profile else None)
            or self.DEFAULT_TIME_BUDGET
        )

        effective_time_budget = compute_effective_time_budget(time_budget)
        avoided_categories = self._merge_avoided_categories(request, profile)
        raw_interests = self._merge_raw_interests(request, profile)
        interests = self._allowed_interests(raw_interests, avoided_categories)
        removed_interests = [item for item in raw_interests if item not in interests]
        avoided_place_ids = self._merge_avoided_places(request, profile)
        budget_level = self._resolve_budget(request, profile)
        pace_mode = self._resolve_pace(request, profile)
        pace_multiplier = mood_to_pace(pace_mode)
        is_visiting = request.is_visiting or False
        visit_city_id = request.visit_city_id
        visit_days = request.visit_days or 1
        local_vs_tourist = 0.5
        novelty_mode = self._resolve_novelty(profile)
        radius = compute_radius(time_budget, is_visiting)
        num_stops = compute_num_stops(effective_time_budget, pace_multiplier)
        min_stop_duration = compute_min_stop_duration(pace_mode)

        return MergedContext(
            location=location,
            city_id=request.city_id,
            start_source=request.start_source,
            start_warnings=list(request.start_warnings or []),
            is_admin=bool(request.is_admin),
            timezone=request.timezone,

            time_budget_minutes=time_budget,
            effective_time_budget_minutes=effective_time_budget,
            time_of_day=request.time_of_day,
            route_time_mode=request.route_time_mode,

            interests=interests,
            interest_removed_due_to_avoidance=removed_interests,
            avoided_categories=avoided_categories,
            avoided_place_ids=avoided_place_ids,

            budget_level=budget_level,

            pace_mode=pace_mode,
            pace_multiplier=pace_multiplier,

            local_vs_tourist=local_vs_tourist,
            novelty_mode=novelty_mode,

            is_visiting=is_visiting,
            visit_city_id=visit_city_id,
            visit_days=visit_days,

            radius_meters=radius,

            effective_num_stops=num_stops,
            min_stop_duration_minutes=min_stop_duration,
            category_affinity=dict(profile.behavior.category_affinity) if profile else {},
            liked_place_ids=list(profile.history.liked_place_ids) if profile else [],
            visited_place_ids=list(profile.history.visited_place_ids) if profile else [],
        )

    def _resolve_location(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> tuple[float, float]:

        if request.location:
            return request.location

        if profile and profile.preferences.home_city_id:
            return (0.0, 0.0)

        raise ValueError("Location is required")

    def _merge_raw_interests(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> List[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in request.interests:
            self._append_unique_clean(result, seen, item)

        if profile:
            for item in profile.preferences.interests:
                self._append_unique_clean(result, seen, item)

        return result

    def _allowed_interests(self, interests: List[str], avoided_categories: List[str]) -> List[str]:
        avoided = {_category_key(item) for item in avoided_categories}
        return [item for item in interests if _category_key(item) not in avoided]

    def _merge_avoided_categories(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> List[str]:

        result = {_category_key(item) for item in request.avoided_categories if _category_key(item)}

        if profile:
            result.update(_category_key(item) for item in profile.preferences.avoided_categories if _category_key(item))

        return list(result)

    def _append_unique_clean(self, result: list[str], seen: set[str], value: object) -> None:
        text = str(value).strip()
        key = _category_key(text)
        if text and key not in seen:
            result.append(text)
            seen.add(key)

    def _merge_avoided_places(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> List[str]:

        result = set(request.excluded_place_ids)

        if profile:
            result.update(profile.history.disliked_place_ids)

        return list(result)

    def _resolve_budget(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> BudgetLevel:

        if request.budget_level is not None:
            return BudgetLevel(request.budget_level)

        if profile and profile.preferences.budget_level is not None:
            return profile.preferences.budget_level

        return self.DEFAULT_BUDGET

    def _resolve_pace(
        self,
        request: RequestContext,
        profile: Optional[UserProfile],
    ) -> PaceMode:

        if request.pace_mode:
            return PaceMode(request.pace_mode)

        if profile and profile.preferences.pace_mode is not None:
            return profile.preferences.pace_mode

        return self.DEFAULT_PACE

    def _resolve_novelty(
        self,
        profile: Optional[UserProfile],
    ) -> bool:

        if not profile:
            return False

        preference = getattr(profile.behavior, "novelty_preference", 0.0)
        completed = int(getattr(profile.behavior, "completed_routes_count", 0) or 0)
        return float(preference or 0.0) > 0.6 or completed >= 3


def _category_key(value: object) -> str:
    text = str(value or "").strip().casefold()
    return text[:-1] if len(text) > 3 and text.endswith("s") else text