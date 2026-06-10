from schemas.place_list_params import PlaceListParams
from services.place_list_params_service import normalize_place_list_params


def test_normalize_place_list_params_combines_search_and_pagination() -> None:
    params = PlaceListParams(
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="  coffee  ",
        limit=10,
        offset=20,
    )

    normalized = normalize_place_list_params(params)

    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "coffee"
    assert normalized.limit == 10
    assert normalized.offset == 20


def test_normalize_place_list_params_converts_blank_q_to_none() -> None:
    params = PlaceListParams(q="   ")

    normalized = normalize_place_list_params(params)

    assert normalized.q is None
    assert normalized.limit == 20
    assert normalized.offset == 0
