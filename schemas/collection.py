from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема подборки.
# Используется для чтения данных о подборке.
class CollectionBase(BaseModel):
    city_id: int
    slug: str
    title: str
    short_description: str | None = None
    is_active: bool = True


# Схема для чтения подборки из базы данных.
class CollectionRead(CollectionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
