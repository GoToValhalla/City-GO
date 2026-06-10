from pydantic import BaseModel, Field

from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


class PlaceSeedValidationResponse(BaseModel):
    """
    Результат валидации одного seed-элемента места.
    """

    is_valid: bool
    title: str
    slug: str
    city_slug: str
    taxonomy_diagnostics: PlaceTaxonomyDiagnosticsResponse
    errors: list[str] = Field(default_factory=list)
