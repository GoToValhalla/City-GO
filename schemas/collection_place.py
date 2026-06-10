from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи подборки и места.
class CollectionPlaceBase(BaseModel):
    collection_id: int
    place_id: int
    position: int = 1


# Схема для чтения связи подборки и места из базы данных.
class CollectionPlaceRead(CollectionPlaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
