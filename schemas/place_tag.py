from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи места и тега.
class PlaceTagBase(BaseModel):
    place_id: int
    tag_id: int


# Схема для чтения связи места и тега из базы данных.
class PlaceTagRead(PlaceTagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
