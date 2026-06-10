from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема категории.
# Используется для чтения данных о категории.
class CategoryBase(BaseModel):
    code: str
    name: str
    is_active: bool = True


# Схема для чтения категории из базы данных.
class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
