from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RouteSessionStatus = Literal["active", "paused", "completed", "abandoned"]
RouteSessionPointAction = Literal["visit", "skip"]


class RouteSessionStartRequest(BaseModel):
    user_key: str | None = Field(default=None, max_length=128)


class RouteSessionUpdateRequest(BaseModel):
    status: Literal["active", "paused", "abandoned"] | None = None
    current_point_index: int | None = Field(default=None, ge=0)


class RouteSessionCheckInRequest(BaseModel):
    point_index: int = Field(ge=0)
    action: RouteSessionPointAction = "visit"


class RouteSessionPointRead(BaseModel):
    place_id: int
    ordering_index: int
    title: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_visited: bool = False
    is_skipped: bool = False
    visited_at: datetime | None = None
    skipped_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RouteSessionRead(BaseModel):
    id: int
    route_id: int
    user_key: str | None = None
    status: RouteSessionStatus
    current_point_index: int
    visited_point_indexes: list[int]
    skipped_point_indexes: list[int]
    started_at: datetime
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    points: list[RouteSessionPointRead] = []

    model_config = ConfigDict(from_attributes=True)


class RouteSessionCompleteResponse(BaseModel):
    id: int
    route_id: int
    status: Literal["completed"]
    visited_points: int
    skipped_points: int
    total_points: int
    completed_at: datetime
