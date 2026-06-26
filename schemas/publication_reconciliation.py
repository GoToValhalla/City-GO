from typing import Any

from pydantic import BaseModel, Field


class PublicationReconciliationApplyRequest(BaseModel):
    confirm: bool = False
    city_slugs: list[str] | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=1000)


class PublicationReconciliationRollbackRequest(BaseModel):
    confirm: bool = False
    audit_ids: list[int] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class PublicationReconciliationResponse(BaseModel):
    changed_places: int
    audit_ids: list[int]
    snapshot: dict[str, Any]


class PublicationReconciliationRollbackResponse(BaseModel):
    restored_places: int
    missing_audit_ids: list[int] = Field(default_factory=list)
