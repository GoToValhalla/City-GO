from pydantic import BaseModel, Field

from schemas.place_seed_validation_response import PlaceSeedValidationResponse


class PlaceSeedBulkValidationResponse(BaseModel):
    """
    Результат bulk-валидации seed-элементов мест.
    """

    total: int
    valid_count: int
    invalid_count: int
    items: list[PlaceSeedValidationResponse] = Field(default_factory=list)
