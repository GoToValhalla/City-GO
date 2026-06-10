from pydantic import BaseModel


class PlaceTaxonomyDiagnosticsResponse(BaseModel):
    """
    Стандартный ответ диагностики taxonomy payload.

    Возвращает только невалидные значения по каждому слою таксономии.
    """

    category: str | None = None
    tags: list[str] = []
    scenario_tags: list[str] = []
    vibe_tags: list[str] = []
    restriction_tags: list[str] = []
