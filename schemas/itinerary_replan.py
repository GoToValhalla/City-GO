from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.itinerary import CurrentRouteContextRead, RouteMode


ReplanReasonType = Literal[
    "coffee_stop",
    "food_stop",
    "rest_stop",
    "shorten_route",
    "continue_from_here",
    "custom",
]


class CurrentRoutePointInput(BaseModel):
    place_id: int
    position: int
    place_slug: str | None = None
    place_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


ReplanRoutePointInput = CurrentRoutePointInput


class CurrentRouteContextInput(BaseModel):
    city_slug: str
    route_mode: RouteMode = "walk"
    points: list[CurrentRoutePointInput] = Field(default_factory=list)
    completed_place_ids: list[int] = Field(default_factory=list)
    remaining_time_minutes: int | None = None
    return_to_start: bool = False
    budget_level: int | None = None


class ReplannedRoutePointRead(BaseModel):
    place_id: int
    position: int
    place_slug: str | None = None
    place_title: str | None = None
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ItineraryReplanRequest(BaseModel):
    current_route: CurrentRouteContextInput
    reason_type: ReplanReasonType
    new_time_budget_minutes: int | None = Field(default=None, ge=15, le=2880)

    # Текущая позиция пользователя.
    current_lat: float | None = None
    current_lng: float | None = None

    # Если пользователь хочет конкретную stop-точку.
    preferred_stop_place_id: int | None = None

    # Свободный текст для custom replan или дополнительных ограничений.
    user_message: str | None = None


class ItineraryReplanResponse(BaseModel):
    status: str = "ok"
    title: str
    summary: str
    estimated_remaining_minutes: int | None = None
    estimated_remaining_distance_km: float | None = None
    points: list[ReplannedRoutePointRead] = Field(default_factory=list)
    current_route_context: CurrentRouteContextRead | None = None
    explanation: str | None = None
