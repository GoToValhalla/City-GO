from pydantic import BaseModel


# Схема входящего AI-запроса.
# Содержит текстовый запрос пользователя и опциональные координаты.
class AIQueryRequest(BaseModel):
    query: str
    lat: float | None = None
    lng: float | None = None
