from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# Уровень бюджета пользователя.
# Используем int enum, чтобы дальше было проще матчить с place.price_level.
class BudgetLevel(int, Enum):
    FREE = 0
    LOW = 1
    MID = 2
    HIGH = 3


# Темп пользователя для построения маршрута.
class PaceMode(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


# Базовые сценарии компании / контекста поездки.
# Пока используем как session-like preference, но храним в профиле как допустимый long-term signal.
class TripVibe(str, Enum):
    SOLO = "solo"
    COUPLE = "couple"
    CHILDREN = "children"
    DOG = "dog"
    FRIENDS = "friends"
    WORK = "work"


# Статические предпочтения пользователя.
# Это слой "что пользователь обычно любит", а не поведение из истории.
class UserStaticPreferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    budget_level: BudgetLevel | None = None
    pace_mode: PaceMode | None = None

    with_children: bool = False
    with_dog: bool = False

    avoided_categories: list[str] = Field(default_factory=list)
    preferred_route_modes: list[str] = Field(default_factory=list)

    # Домашний город пригодится для cold start, safe default и travel mode.
    home_city_id: str | None = None

    model_config = ConfigDict(use_enum_values=True)


# Минимальный исторический слой.
# Это именно данные для дедупликации, penalties и простого personalization,
# без сложного event-log и decay логики.
class UserHistory(BaseModel):
    visited_place_ids: list[str] = Field(default_factory=list)
    visited_city_ids: list[str] = Field(default_factory=list)

    liked_place_ids: list[str] = Field(default_factory=list)
    disliked_place_ids: list[str] = Field(default_factory=list)

    # Последний маршрут нужен для repetition penalty.
    last_route_place_ids: list[str] = Field(default_factory=list)

    # Несколько последних маршрутов пригодятся для более сильного diversity control.
    last_3_routes_place_ids: list[list[str]] = Field(default_factory=list)

    # Храним агрегат по пропускам.
    # Формат:
    # {
    #   "place_slug": {
    #       "count": 2,
    #       "last_skipped": "2025-04-10T12:00:00"
    #   }
    # }
    skipped_place_ids: dict[str, dict] = Field(default_factory=dict)


# Поведенческий слой.
# Часть полей понадобится не сразу, но схема закладывается сейчас,
# чтобы не ломать контракт позже.
class UserBehaviorProfile(BaseModel):
    category_affinity: dict[str, float] = Field(default_factory=dict)
    tag_affinity: dict[str, float] = Field(default_factory=dict)

    # Отношение фактического времени на точке к ожидаемому.
    # 1.0 = проводит примерно столько же, сколько прогнозировали.
    avg_dwell_ratio: float = Field(default=1.0, ge=0.1, le=5.0)

    # Доля пропущенных точек внутри маршрутов.
    skip_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # Средний предпочитаемый бюджет времени маршрута.
    preferred_time_budget_minutes: int | None = Field(default=None, ge=15, le=1440)

    # Какие vibes чаще встречаются в завершённых сессиях.
    preferred_trip_vibes: list[TripVibe] = Field(default_factory=list)

    completed_routes_count: int = Field(default=0, ge=0)
    total_sessions_count: int = Field(default=0, ge=0)

    last_active_date: datetime | None = None

    model_config = ConfigDict(use_enum_values=True)


# Единый профиль пользователя для recommendation / itinerary logic.
# Это основной контракт между profile service и recommendation pipeline.
class UserProfile(BaseModel):
    user_id: int | None = None

    preferences: UserStaticPreferences = Field(default_factory=UserStaticPreferences)
    history: UserHistory = Field(default_factory=UserHistory)
    behavior: UserBehaviorProfile = Field(default_factory=UserBehaviorProfile)

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(use_enum_values=True)
