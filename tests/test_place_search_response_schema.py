import pytest
from pydantic import ValidationError

from schemas.place_search_response import PlaceSearchResponse


def test_place_search_response_accepts_valid_payload() -> None:
    response = PlaceSearchResponse(
        items=[],
        total=0,
        limit=20,
        offset=0,
    )

    assert response.items == []
    assert response.total == 0
    assert response.limit == 20
    assert response.offset == 0


def test_place_search_response_requires_total() -> None:
    with pytest.raises(ValidationError):
        PlaceSearchResponse(
            items=[],
            limit=20,
            offset=0,
        )
