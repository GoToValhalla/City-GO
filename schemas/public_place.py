from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PublicCategory(BaseModel):
    slug: str | None = None
    label: str


class PublicCoordinates(BaseModel):
    lat: float | None = None
    lng: float | None = None


class PublicDataQuality(BaseModel):
    is_degraded: bool
    completeness_score: int
    source_freshness_days: int | None = None


class PublicPlaceRead(BaseModel):
    id: int
    slug: str
    name: str
    title: str
    category: str
    category_label: str
    category_info: PublicCategory
    description: str | None = None
    short_description: str | None = None
    address: str | None = None
    coordinates: PublicCoordinates
    lat: float | None = None
    lng: float | None = None
    image_url: str | None = None
    image_urls: list[str] | None = None
    photo_urls: list[str] | None = None
    opening_hours: Any | None = None
    operating_hours: Any | None = None
    average_visit_duration_minutes: int | None = None
    price_level: int | None = None
    dog_friendly: bool = False
    family_friendly: bool = False
    indoor: bool = False
    outdoor: bool = False
    phone: str | None = None
    website: str | None = None
    data_quality: PublicDataQuality

    model_config = ConfigDict(extra="forbid")


class PublicPlaceSearchResponse(BaseModel):
    items: list[PublicPlaceRead]
    total: int
    limit: int
    offset: int
