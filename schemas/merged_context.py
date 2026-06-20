"""
Единый контекст запроса на построение маршрута (recommendation pipeline): гео, время, ограничения.
"""

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict


# -----------------------------
# ENUMS — перечисления уровня бюджета и темпа.
# -----------------------------
class BudgetLevel(int, Enum):
    FREE = 0
    LOW = 1
    MID = 2
    HIGH = 3


class PaceMode(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


# -----------------------------
# CORE MODEL — основная модель контекста одного запроса на маршрут.
# -----------------------------
class MergedContext(BaseModel):
    """
    ЕДИНЫЙ ОБЪЕКТ КОНТЕКСТА

    Канон данных для одного запроса (source of truth на время построения маршрута).
    Передаётся через весь пайплайн без изменения по ссылке (иммутабельное использование).
    """

    # --- LOCATION — стартовые координаты (широта, долгота).
    location: Tuple[float, float]  # (lat, lng)
    city_id: Optional[str] = None

    # --- TIME — лимиты времени на маршрут.
    time_budget_minutes: int
    effective_time_budget_minutes: int
    time_of_day: Optional[str] = None
    route_time_mode: str = "flexible"
    require_known_hours: bool = False

    # --- USER INTENT — интересы и исключения пользователя.
    interests: List[str] = Field(default_factory=list)
    interest_removed_due_to_avoidance: List[str] = Field(default_factory=list)

    avoided_categories: List[str] = Field(default_factory=list)
    avoided_place_ids: List[str] = Field(default_factory=list)

    # --- CONSTRAINTS — жёсткие ограничения (уровень цен).
    budget_level: BudgetLevel

    # --- BEHAVIOR / STYLE — темп и баланс «локальный / туристический» стиль.
    pace_mode: PaceMode
    pace_multiplier: float

    local_vs_tourist: float  # 0..1

    # --- STRATEGY FLAGS — флаги стратегии (новизна, визит).
    novelty_mode: bool

    is_visiting: bool
    visit_city_id: Optional[str] = None
    visit_days: int = 1

    # --- GEO — радиус поиска кандидатов вокруг старта.
    radius_meters: int

    # --- ROUTE SHAPE — целевое число остановок и минимальная длительность визита.
    effective_num_stops: int
    min_stop_duration_minutes: int

    # --- PERSONALIZATION — derived profile signals, optional and soft.
    category_affinity: dict[str, float] = Field(default_factory=dict)
    liked_place_ids: list[str] = Field(default_factory=list)
    visited_place_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=True)


# -----------------------------
# HELPERS — функции расчёта радиуса, бюджета времени и числа остановок.
# -----------------------------
def mood_to_pace(pace_mode: PaceMode) -> float:
    """
    Преобразует pace_mode в multiplier времени на точке.
    """
    if pace_mode == PaceMode.SLOW:
        return 1.3
    if pace_mode == PaceMode.FAST:
        return 0.8
    return 1.0


def compute_radius(
    time_budget_minutes: int,
    is_visiting: bool = False,
) -> int:
    """
    Определяет радиус поиска кандидатов.
    """
    if is_visiting:
        return 5000

    if time_budget_minutes <= 60:
        return 2500
    if time_budget_minutes <= 120:
        return 5000
    if time_budget_minutes <= 240:
        return 6500

    return 8000


def compute_effective_time_budget(time_budget_minutes: int) -> int:
    """
    Возвращает полный пользовательский бюджет маршрута.

    Раньше здесь снималось 20% на overhead, но сам route pipeline уже считает walking
    minutes между точками. Получалось двойное списание времени: 240 минут превращались
    в 192, а затем из них ещё вычитались переходы. Для пользовательского маршрута
    effective budget должен совпадать с выбранным временем.
    """
    return int(time_budget_minutes)


def compute_num_stops(
    effective_time_budget: int,
    pace_multiplier: float,
) -> int:
    """
    Определяет продуктовую цель по количеству точек маршрута.
    """
    if effective_time_budget <= 60:
        target = 2
    elif effective_time_budget <= 120:
        target = 4
    elif effective_time_budget <= 240:
        target = 6
    else:
        target = 8

    if pace_multiplier >= 1.25:
        target -= 1
    elif pace_multiplier <= 0.85:
        target += 1

    return max(1, min(target, 8))


def compute_min_stop_duration(pace_mode: PaceMode) -> int:
    """
    Минимально допустимое время на точке.
    """
    if pace_mode == PaceMode.SLOW:
        return 25
    if pace_mode == PaceMode.FAST:
        return 15
    return 20
