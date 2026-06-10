from pydantic import BaseModel


# Схема ответа для списка мест, которые открыты сейчас.
class OpenNowPlaceRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    category_id: int | None = None
    category: str
    address: str
    open_time: str
    close_time: str
