from pydantic import BaseModel, Field


class PlaceTaxonomyPayload(BaseModel):
    """
    Каноничный payload для таксономии места.

    Используем как заготовку для:
    - seed-данных
    - импорта
    - AI enrichment
    - будущей backend-валидации
    """

    category: str
    tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    restriction_tags: list[str] = Field(default_factory=list)
