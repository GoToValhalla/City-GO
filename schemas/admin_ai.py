from __future__ import annotations

from pydantic import BaseModel, Field


class AdminAIModelOption(BaseModel):
    value: str
    label: str
    model: str
    description: str


class AdminAITaskOption(BaseModel):
    id: str
    label: str
    description: str
    result_mode: str
    risk_level: str
    enabled: bool = True


class AdminAITasksResponse(BaseModel):
    tasks: list[AdminAITaskOption]
    model_options: list[AdminAIModelOption]
    default_task_id: str
    default_model_mode: str


class AdminAIRunRequest(BaseModel):
    task_id: str
    city_slug: str
    model_mode: str = "economy"
    limit: int = Field(default=10, ge=1, le=100)
    apply_safe_changes: bool = True


class AdminAIResultItem(BaseModel):
    place_id: int | None = None
    title: str
    summary: str
    recommended_action: str
    confidence: float | None = None


class AdminAIRunResult(BaseModel):
    task_id: str
    task_label: str
    city_slug: str
    model: str
    status: str
    rows_processed: int
    rows_updated: int
    applied: bool
    batch_id: str | None = None
    items: list[AdminAIResultItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    message: str
    next_action: str
