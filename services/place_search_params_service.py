"""
Нормализация строки поиска `q` и связанных полей PlaceSearchParams.
"""

from schemas.place_search import PlaceSearchParams


def normalize_place_search_params(params: PlaceSearchParams) -> PlaceSearchParams:
    """
    Нормализует параметры поиска мест.

    Пока:
    - обрезаем пробелы у q
    - пустую строку превращаем в None

    Позже сюда можно добавить:
    - lower()
    - alias-логику
    - валидацию конфликтующих фильтров
    """
    q = params.q.strip() if params.q else None

    if q == "":
        q = None

    return PlaceSearchParams(
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
        q=q,
    )
