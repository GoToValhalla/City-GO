import pytest
from pydantic import ValidationError

from schemas.place_list_params import PlaceListParams


def test_place_list_params_defaults() -> None:
    params = PlaceListParams()

    assert params.limit == 20
    assert params.offset == 0
    assert params.q is None


def test_place_list_params_rejects_zero_limit() -> None:
    with pytest.raises(ValidationError):
        PlaceListParams(limit=0)


def test_place_list_params_rejects_negative_offset() -> None:
    with pytest.raises(ValidationError):
        PlaceListParams(offset=-1)
