from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlaceDiscoveryCreate(BaseModel):
    city_slug: str
    name: str
    source_type: str = "user_report"
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    category_hint: str | None = None
    submitted_by_telegram_user_id: int | None = None


class PlaceDiscoveryRead(BaseModel):
    id: int
    city_id: int
    name: str
    status: str
    source_type: str
    duplicate_place_id: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
