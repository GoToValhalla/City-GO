from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SystemLogRead(BaseModel):
    id: int
    level: str
    module: str
    message: str
    details: dict[str, object] | None = None
    city_slug: str | None = None
    place_id: int | None = None
    route_id: str | None = None
    request_id: str | None = None
    actor_id: str | None = None
    environment: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SystemLogListResponse(BaseModel):
    items: list[SystemLogRead]
    total: int
    limit: int
    offset: int
