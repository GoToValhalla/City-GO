from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def test_place_seed_bulk_validation_response_keeps_counts_independent_from_items_length() -> None:
    item = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    response = PlaceSeedBulkValidationResponse(
        total=10,
        valid_count=7,
        invalid_count=3,
        items=[item],
    )

    assert response.total == 10
    assert response.valid_count == 7
    assert response.invalid_count == 3
    assert len(response.items) == 1
