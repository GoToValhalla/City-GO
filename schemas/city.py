from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема города.
# Содержит общие поля для чтения данных о городе.
class CityBase(BaseModel):
    slug: str
    name: str
    region: str | None = None
    country: str = "Россия"
    timezone: str = "Europe/Kaliningrad"
    center_lat: float | None = None
    center_lng: float | None = None
    launch_status: str = "published"
    country_id: int | None = None
    region_id: int | None = None
    city_candidate_id: int | None = None
    bbox: dict[str, object] | None = None
    is_active: bool = True


class CityAvailableRead(BaseModel):
    slug: str
    name: str
    country: str
    region: str | None = None
    launch_status: str
    places_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# Схема для чтения города из базы данных.
class CityRead(CityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)