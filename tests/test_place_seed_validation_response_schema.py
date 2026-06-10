from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def test_place_seed_validation_response_accepts_valid_payload() -> None:
    response = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    assert response.is_valid is True
    assert response.title == "Coffee Point"
    assert response.slug == "coffee-point"
    assert response.city_slug == "zelenogradsk"
    assert response.errors == []


def test_place_seed_validation_response_accepts_errors() -> None:
    response = PlaceSeedValidationResponse(
        is_valid=False,
        title=" ",
        slug=" ",
        city_slug=" ",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(
            category="bad_category",
            tags=["bad_tag"],
            scenario_tags=[],
            vibe_tags=[],
            restriction_tags=[],
        ),
        errors=["title is empty", "slug is empty", "city_slug is empty"],
    )

    assert response.is_valid is False
    assert response.taxonomy_diagnostics.category == "bad_category"
    assert response.taxonomy_diagnostics.tags == ["bad_tag"]
    assert "title is empty" in response.errors
