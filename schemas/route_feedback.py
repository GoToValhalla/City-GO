from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


_ALLOWED_SOURCES = {"web", "telegram"}
_ALLOWED_PROBLEM_TYPES = {
    "bad_route",
    "wrong_place",
    "too_long",
    "too_short",
}


class RouteFeedbackCreate(BaseModel):
    """Входной контракт оценки маршрута из web/Telegram UI."""

    route_id: str = Field(min_length=1, max_length=255)
    user_id: str | None = Field(default=None, max_length=100)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="web", max_length=32)
    route_payload: dict[str, object] | None = None
    liked_place_ids: list[str] = Field(default_factory=list)
    disliked_place_ids: list[str] = Field(default_factory=list)
    skipped_place_ids: list[str] = Field(default_factory=list)
    problem_types: list[str] = Field(default_factory=list)

    @field_validator("route_id")
    @classmethod
    def normalize_route_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("route_id must not be blank")
        return normalized

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "tma":
            normalized = "telegram"
        if normalized not in _ALLOWED_SOURCES:
            raise ValueError("unsupported feedback source")
        return normalized

    @field_validator("problem_types")
    @classmethod
    def normalize_problem_types(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip().lower()
            if item not in _ALLOWED_PROBLEM_TYPES:
                raise ValueError("unsupported feedback problem type")
            if item not in normalized:
                normalized.append(item)
        return normalized


class RouteFeedbackRead(BaseModel):
    """Ответ после сохранения feedback-сигнала в user_signals."""

    id: int
    user_id: str
    signal_type: str
    entity_type: str
    entity_id: str
    payload: dict[str, object] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
