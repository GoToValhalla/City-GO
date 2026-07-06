"""
Объединённая нормализация query-параметров списка мест (пагинация, поиск, сортировка).
"""

from schemas.place_query_params import PlaceQueryParams
from schemas.place_list_params import PlaceListParams
from schemas.sorting import SortingParams
from services.place_list_params_service import normalize_place_list_params
from services.sorting_service import normalize_sorting_params


def normalize_place_query_params(params: PlaceQueryParams) -> PlaceQueryParams:
    """
    Нормализует единые параметры запроса по местам.

    Объединяет:
    - нормализацию list/search-параметров
    - нормализацию sorting-параметров
    """
    normalized_list = normalize_place_list_params(
        PlaceListParams(
            city_id=params.city_id,
            city_slug=params.city_slug,
            destination_slug=params.destination_slug,
            category_id=params.category_id,
            tag_id=params.tag_id,
            q=params.q,
            limit=params.limit,
            offset=params.offset,
        )
    )

    normalized_sorting = normalize_sorting_params(
        SortingParams(
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
    )

    return PlaceQueryParams(
        city_id=normalized_list.city_id,
        city_slug=normalized_list.city_slug,
        destination_slug=normalized_list.destination_slug,
        category_id=normalized_list.category_id,
        tag_id=normalized_list.tag_id,
        q=normalized_list.q,
        limit=normalized_list.limit,
        offset=normalized_list.offset,
        sort_by=normalized_sorting.sort_by,
        sort_order=normalized_sorting.sort_order,
    )
