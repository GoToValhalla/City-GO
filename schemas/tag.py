from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема тега.
# Используется для чтения данных о теге.
class TagBase(BaseModel):
    code: str
    name: str
    is_active: bool = True


# Схема для чтения тега из базы данных.
class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
