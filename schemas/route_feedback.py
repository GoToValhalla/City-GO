from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
