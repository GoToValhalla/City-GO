from pydantic import BaseModel, Field


class PlaceTaxonomyResponse(BaseModel):
    """
    Стандартный ответ для каноничной таксономии City GO.
    """

    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    restriction_tags: list[str] = Field(default_factory=list)
    user_signals: list[str] = Field(default_factory=list)
