from pydantic import BaseModel, Field


class ProjectionRebuildRequest(BaseModel):
    projection_type: str
    city_id: int | None = Field(default=None, ge=1)
    source: str = "admin_api"
    audit_context: dict[str, object] = Field(default_factory=dict)


class ProjectionReadinessResponse(BaseModel):
    projection_type: str
    city_id: int | None
    ready: bool
    reason: str
    source_version: int | None
    projection_version: int | None
    expected_count: int
    actual_count: int
    latest_job_id: int | None
    last_successful_job_id: int | None
    activation_safe: bool
    latest_rebuild_job: dict[str, object] | None = None
    last_successful_rebuild: dict[str, object] | None = None
    last_failure_reason: str | None = None
    active_toggles: dict[str, bool] = Field(default_factory=dict)
