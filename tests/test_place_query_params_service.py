from schemas.place_query_params import PlaceQueryParams
from services.place_query_params_service import normalize_place_query_params


def test_normalize_place_query_params_combines_list_and_sorting() -> None:
    params = PlaceQueryParams(
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="  coffee  ",
        limit=10,
        offset=20,
        sort_by="created_at",
        sort_order="desc",
    )

    normalized = normalize_place_query_params(params)

    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "coffee"
    assert normalized.limit == 10
    assert normalized.offset == 20
    assert normalized.sort_by == "created_at"
    assert normalized.sort_order == "desc"


def test_normalize_place_query_params_uses_defaults() -> None:
    params = PlaceQueryParams()

    normalized = normalize_place_query_params(params)

    assert normalized.q is None
    assert normalized.limit == 20
    assert normalized.offset == 0
    assert normalized.sort_by == "title"
    assert normalized.sort_order == "asc"
