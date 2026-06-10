from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи маршрута и места.
class RoutePlaceBase(BaseModel):
    route_id: int
    place_id: int
    position: int = 1


# Схема для чтения связи маршрута и места из базы данных.
class RoutePlaceRead(RoutePlaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
