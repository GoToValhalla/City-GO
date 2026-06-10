from schemas.place_search import PlaceSearchParams
from services.place_search_params_service import normalize_place_search_params


def test_normalize_place_search_params_trims_q() -> None:
    params = PlaceSearchParams(q="  coffee  ")

    normalized = normalize_place_search_params(params)

    assert normalized.q == "coffee"


def test_normalize_place_search_params_converts_empty_q_to_none() -> None:
    params = PlaceSearchParams(q="   ")

    normalized = normalize_place_search_params(params)

    assert normalized.q is None


def test_normalize_place_search_params_keeps_other_filters() -> None:
    params = PlaceSearchParams(
        city_id=1,
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="walk",
    )

    normalized = normalize_place_search_params(params)

    assert normalized.city_id == 1
    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "walk"
