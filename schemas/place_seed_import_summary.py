from pydantic import BaseModel, Field


class PlaceSeedImportSummary(BaseModel):
    """
    Краткая сводка по seed-импорту мест.

    Счётчики auto_published / needs_review_count / rejected_count отражают
    решения Import Quality Gate для новых мест.
    """

    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    invalid: int = 0
    errors: list[str] = Field(default_factory=list)
    # Quality Gate разбивка для новых мест
    auto_published: int = 0
    needs_review_count: int = 0
    rejected_count: int = 0
