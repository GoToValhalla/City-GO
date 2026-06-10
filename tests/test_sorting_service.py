from schemas.sorting import SortingParams
from services.sorting_service import normalize_sorting_params


def test_normalize_sorting_params_keeps_values() -> None:
    params = SortingParams(
        sort_by="created_at",
        sort_order="desc",
    )

    normalized = normalize_sorting_params(params)

    assert normalized.sort_by == "created_at"
    assert normalized.sort_order == "desc"


def test_sorting_params_default_values() -> None:
    params = SortingParams()

    normalized = normalize_sorting_params(params)

    assert normalized.sort_by == "title"
    assert normalized.sort_order == "asc"
