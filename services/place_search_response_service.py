from schemas.place_search_response import PlaceSearchResponse


def build_place_search_response(
    items,
    total: int,
    limit: int,
    offset: int,
) -> PlaceSearchResponse:
    """
    Собирает стандартный ответ для list/search сценариев по местам.
    """
    return PlaceSearchResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
