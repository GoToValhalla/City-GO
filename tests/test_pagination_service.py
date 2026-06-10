from schemas.pagination import PaginationParams
from services.pagination_service import normalize_pagination_params


def test_normalize_pagination_params_keeps_values() -> None:
    params = PaginationParams(limit=10, offset=20)

    normalized = normalize_pagination_params(params)

    assert normalized.limit == 10
    assert normalized.offset == 20


def test_pagination_params_default_values() -> None:
    params = PaginationParams()

    normalized = normalize_pagination_params(params)

    assert normalized.limit == 20
    assert normalized.offset == 0
