from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WalkingRoutePoint(BaseModel):
    lat: float
    lng: float

    @field_validator("lat")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("lng")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return value


class WalkingRouteRequest(BaseModel):
    points: list[WalkingRoutePoint] = Field(min_length=2, max_length=25)


class WalkingRouteStep(BaseModel):
    instruction: str
    street_name: str | None = None
    distance_meters: float
    duration_seconds: float


class WalkingRouteLeg(BaseModel):
    from_index: int
    to_index: int
    distance_meters: float
    duration_seconds: float
    steps: list[WalkingRouteStep]


class WalkingRouteResponse(BaseModel):
    status: Literal["routed", "unavailable"]
    provider: str
    geometry: list[tuple[float, float]]
    distance_meters: float | None = None
    duration_seconds: float | None = None
    legs: list[WalkingRouteLeg] = []
    warning: str | None = None
