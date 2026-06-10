"""
Нормализация параметров списка мест (search + pagination).
"""

from schemas.place_list_params import PlaceListParams
from schemas.place_search import PlaceSearchParams
from schemas.pagination import PaginationParams
from services.place_search_params_service import normalize_place_search_params
from services.pagination_service import normalize_pagination_params


def normalize_place_list_params(params: PlaceListParams) -> PlaceListParams:
    """
    Нормализует объединенные параметры списка мест.

    Объединяет:
    - нормализацию search-параметров
    - нормализацию pagination-параметров
    """
    normalized_search = normalize_place_search_params(
        PlaceSearchParams(
            city_id=params.city_id,
            city_slug=params.city_slug,
            category_id=params.category_id,
            tag_id=params.tag_id,
            q=params.q,
        )
    )

    normalized_pagination = normalize_pagination_params(
        PaginationParams(
            limit=params.limit,
            offset=params.offset,
        )
    )

    return PlaceListParams(
        city_id=normalized_search.city_id,
        city_slug=normalized_search.city_slug,
        category_id=normalized_search.category_id,
        tag_id=normalized_search.tag_id,
        q=normalized_search.q,
        limit=normalized_pagination.limit,
        offset=normalized_pagination.offset,
    )
