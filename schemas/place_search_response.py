from pydantic import BaseModel

from schemas.place import PlaceRead


class PlaceSearchResponse(BaseModel):
    """
    Стандартный ответ для list/search сценариев по местам.

    Пока это подготовка под следующий шаг:
    позже можно будет перевести /places/ и /places/search/
    с list[PlaceRead] на более стабильный контракт с метаданными.
    """

    items: list[PlaceRead]
    total: int
    limit: int
    offset: int
