"""
Шаг 4 пайплайна: мягкий скоринг (soft scoring) — только поля Place и MergedContext (без ORM-расширений).

Слот разбивки «popularity» исторически нейтрален: на Place нет popularity_score,
поэтому здесь он означает «насколько цена места согласуется с budget_level».

Компонент data_quality_score читает place.validation (если навешан пайплайном после retrieval):
штрафы только по уже известным кодам issues из place_validation_service, без новых правил.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from models.place import Place
from schemas.merged_context import MergedContext
from services.itinerary_time_service import is_place_open_at_time
from services.place_runtime_defaults import effective_opening_hours, effective_visit_duration
from services.personalization_score import personalization_score
from services.route_base_quality_score import base_quality_score
from services.route_data_confidence_score import data_confidence_score
from services.route_interest_mapping import interest_match_score
from services.route_popularity_proxy import popularity_proxy_score
from services.route_start_time import effective_route_start
from services.route_time_context_score import time_context_score


# Коды issues из services.place_validation_service — штраф за каждое вхождение (сумма, затем clip в [0, 1]).
_ISSUE_PENALTY_LAT_LNG = frozenset(
    {
        "lat_missing",
        "lat_invalid_type",
        "lat_out_of_range",
        "lng_missing",
        "lng_invalid_type",
        "lng_out_of_range",
    }
)
_ISSUE_PENALTY_OPENING_HOURS = frozenset(
    {
        "opening_hours_invalid_type",
        "opening_hours_day_invalid",
        "opening_hours_unknown_key",
        "opening_hours_time_not_string",
        "opening_hours_empty_time_string",
        "opening_hours_unparseable_time",
    }
)
_ISSUE_PENALTY_VISIT_DURATION = frozenset(
    {
        "visit_duration_invalid_type",
        "visit_duration_non_positive",
    }
)
_ISSUE_PENALTY_SOFT = frozenset(
    {
        "category_empty",
        "price_level_invalid_type",
        "price_level_out_of_range",
    }
)

# Веса штрафов: lat/lng сильнее всего, затем часы, длительность визита, мягко — категория/цена.
_PENALTY_LAT_LNG = 0.22
_PENALTY_OPENING = 0.14
_PENALTY_VISIT = 0.09
_PENALTY_SOFT = 0.05


def is_place_open_at(place: Place, dt: datetime) -> bool | None:
    return is_place_open_at_time(effective_opening_hours(place), dt)


class ScoredPlace:
    def __init__(self, place: Place, score: float, breakdown: Dict[str, float]):
        self.place = place
        self.score = score
        self.breakdown = breakdown


class ScoringService:
    """
    Шаг 4: мягкий скоринг кандидатов.

    Задача:
    - присвоить каждому месту score [0..1]
    - сохранить breakdown (для explainability)
    - НЕ выбирать маршрут (это следующий шаг)

    Контракт ORM Place (только реальные поля):
    - category, lat/lng, price_level, outdoor/indoor, dog_friendly, family_friendly,
      average_visit_duration_minutes, opening_hours (через is_place_open_at)
    - нет popularity_score / tags / city_id / active — не используются

    Дополнительно (не колонка БД): place.validation — dict с ключом issues (список строк),
    если оркестратор уже вызвал validate_place; иначе data_quality нейтрален (1.0).
    """

    def score(
        self,
        places: List[Place],
        ctx: MergedContext,
    ) -> List[ScoredPlace]:

        scored = []

        for place in places:
            breakdown = self._compute_breakdown(place, ctx)
            final_score = self._combine_scores(breakdown)

            scored.append(ScoredPlace(place, final_score, breakdown))

        scored.sort(key=lambda x: x.score, reverse=True)

        return scored

    # -----------------------------
    # BREAKDOWN — вклад по осям interest/distance/context/price/novelty/data_quality.
    # -----------------------------

    def _compute_breakdown(
        self,
        place: Place,
        ctx: MergedContext,
    ) -> Dict[str, float]:

        return {
            "base_quality": base_quality_score(place),
            "interest": self._interest_score(place, ctx),
            "distance": self._distance_score(place, ctx),
            "context": self._context_score(place, ctx),
            "popularity": self._price_budget_score(place, ctx),
            "novelty": self._novelty_score(place, ctx),
            "data_quality": self._data_quality_score(place),
            "time_context": time_context_score(place, getattr(ctx, "time_of_day", None)),
            "data_confidence": data_confidence_score(place),
            "popularity_proxy": popularity_proxy_score(place),
            "personalization": personalization_score(place, ctx),
        }

    # -----------------------------
    # FINAL SCORE — взвешенная сумма компонентов breakdown.
    # -----------------------------

    def _combine_scores(self, b: Dict[str, float]) -> float:
        """
        Веса: основные сигналы без изменения доминирования; data_quality — небольшой корректирующий вес.
        """

        score = (
            b["base_quality"] * 0.18
            + b["interest"] * 0.27
            + b["time_context"] * 0.18
            + b["data_confidence"] * 0.14
            + b["popularity_proxy"] * 0.08
            + b["context"] * 0.07
            + b["data_quality"] * 0.04
            + b["personalization"] * 0.04
        )
        return max(0.0, min(1.0, score))

    # -----------------------------
    # COMPONENTS — расчёт отдельных компонентов оценки для одного места.
    # -----------------------------

    def _data_quality_score(self, place: Place) -> float:
        """
        [0, 1]: 1.0 — нет validation или нет issues; чем больше проблем, тем ниже (нижняя граница 0).
        """
        raw = getattr(place, "validation", None)
        if not isinstance(raw, dict):
            return 1.0

        issues = raw.get("issues")
        if not isinstance(issues, list) or len(issues) == 0:
            return 1.0

        penalty = 0.0
        for item in issues:
            if not isinstance(item, str):
                continue
            code = item
            if code in _ISSUE_PENALTY_LAT_LNG:
                penalty += _PENALTY_LAT_LNG
            elif code in _ISSUE_PENALTY_OPENING_HOURS:
                penalty += _PENALTY_OPENING
            elif code in _ISSUE_PENALTY_VISIT_DURATION:
                penalty += _PENALTY_VISIT
            elif code in _ISSUE_PENALTY_SOFT:
                penalty += _PENALTY_SOFT

        return max(0.0, min(1.0, 1.0 - penalty))

    def _interest_score(self, place: Place, ctx: MergedContext) -> float:
        """
        Семантическое совпадение interest → category/tag.
        Не фильтрует место: только даёт boost в общем scoring.
        """
        score = interest_match_score(place, list(ctx.interests))
        return 0.22 if ctx.interests and not (place.category or "").strip() else score

    def _distance_score(self, place: Place, ctx: MergedContext) -> float:
        """
        Близость к стартовой точке; масштаб привязан к radius_meters из контекста.
        """
        if place.lat is None or place.lng is None:
            return 0.0

        lat, lng = ctx.location

        dist = ((place.lat - lat) ** 2 + (place.lng - lng) ** 2) ** 0.5

        # ~ метры широты на градус; радиус из контекста в «градусы» для нормализации
        max_dist = max(ctx.radius_meters / 111_000.0, 1e-5)

        score = max(0.0, 1.0 - (dist / max_dist))
        return min(score, 1.0)

    def _context_score(self, place: Place, ctx: MergedContext) -> float:
        """
        Вену: indoor/outdoor, семья/собака, плавное соответствие dwell pace_mode,
        мягкий сигнал по opening_hours «сейчас» (не дублирует hard filter).
        """
        base = 0.52

        if ctx.is_visiting and bool(getattr(place, "outdoor", False)):
            base += 0.16
        elif not ctx.is_visiting and bool(getattr(place, "indoor", False)):
            base += 0.07

        if bool(getattr(place, "family_friendly", False)):
            base += 0.05
        if bool(getattr(place, "dog_friendly", False)):
            base += 0.04

        dwell = effective_visit_duration(place)

        pace = ctx.pace_mode
        if pace == "fast" and dwell > 50:
            base -= 0.07
        elif pace == "slow" and dwell < 18:
            base -= 0.05

        # Мягкая «открытость сейчас»: закрыто — не убиваем кандидата, но опускаем приоритет.
        open_state = is_place_open_at(place, effective_route_start(datetime.utcnow(), ctx.time_of_day))
        if open_state is True:
            base += 0.12
        elif open_state is False:
            base -= 0.14
        # None — нет данных, не двигаем base

        return max(0.0, min(1.0, base))

    def _price_budget_score(self, place: Place, ctx: MergedContext) -> float:
        """
        Согласование price_level места с budget_level пользователя (int 0..3).
        """
        pl = place.price_level
        try:
            bl = int(ctx.budget_level)
        except (TypeError, ValueError):
            bl = 2

        if pl is None:
            return 0.58

        if pl <= bl:
            return 0.82 + 0.18 * (1.0 - (bl - pl) / max(bl + 1, 1))

        over = pl - bl
        return max(0.12, 0.85 - 0.22 * over)

    def _novelty_score(self, _place: Place, ctx: MergedContext) -> float:
        """
        Режим новизны из контекста; без истории посещений на MergedContext — только флаг.
        """
        if ctx.novelty_mode:
            return 1.0

        return 0.32
