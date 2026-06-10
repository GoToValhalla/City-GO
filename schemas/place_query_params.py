from schemas.place_list_params import PlaceListParams
from schemas.sorting import SortingParams


class PlaceQueryParams(PlaceListParams, SortingParams):
    """
    Единые параметры запроса для places/search сценариев.

    Объединяет:
    - фильтры
    - текстовый поиск
    - пагинацию
    - сортировку
    """

    pass
