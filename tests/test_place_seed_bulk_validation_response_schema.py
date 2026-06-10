from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from schemas.place_seed_validation_response import PlaceSeedValidationResponse


def test_place_seed_bulk_validation_response_defaults() -> None:
    response = PlaceSeedBulkValidationResponse(
        total=0,
        valid_count=0,
        invalid_count=0,
    )

    assert response.total == 0
    assert response.valid_count == 0
    assert response.invalid_count == 0
    assert response.items == []


def test_place_seed_bulk_validation_response_accepts_items() -> None:
    item = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    response = PlaceSeedBulkValidationResponse(
        total=1,
        valid_count=1,
        invalid_count=0,
        items=[item],
    )

    assert response.total == 1
    assert response.valid_count == 1
    assert response.invalid_count == 0
    assert len(response.items) == 1
    assert response.items[0].title == "Coffee Point"
