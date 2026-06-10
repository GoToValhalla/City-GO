from pydantic import BaseModel


# Схема ответа для nearby-поиска.
class NearbyPlaceRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    category_id: int | None = None
    category: str
    address: str
    lat: float
    lng: float
    distance_km: float
