from pydantic import BaseModel


class CityStartPointRead(BaseModel):
    id: int | None = None
    label_ru: str
    label_en: str | None = None
    lat: float
    lng: float
    type: str
    sort_order: int = 0
    place_id: int | None = None


class ResolveStartRequest(BaseModel):
    city_slug: str
    type: str = "city_center"
    lat: float | None = None
    lng: float | None = None
    query: str | None = None
    place_id: int | None = None


class ResolveStartResponse(BaseModel):
    type: str
    lat: float
    lng: float
    label: str
    out_of_city: bool = False
    warnings: list[dict[str, str]] = []
    candidates: list[CityStartPointRead] = []
