from pydantic import BaseModel

from schemas.pagination import PaginationParams


class PlaceListParams(PaginationParams):
    """
    Параметры list/search для мест.

    Объединяет:
    - фильтры places
    - текстовый поиск
    - пагинацию
    """

    city_id: int | None = None
    city_slug: str | None = None
    destination_slug: str | None = None
    category_id: int | None = None
    tag_id: int | None = None
    q: str | None = None
