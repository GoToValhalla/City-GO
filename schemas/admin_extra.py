"""LEGACY SCHEMAS for the unregistered `routers.admin_extra` router.

Status: historical compatibility only.

These response contracts belonged to the first admin UI extra endpoints:
- `/admin/roles`
- `/admin/cities/{city_id}/coverage`
- `/admin/route-feedback`

Active replacements live in the dedicated admin overview, coverage, platform and
route feedback schemas/services. Do not use these schemas for new endpoints.
"""

from datetime import datetime
from pydantic import BaseModel


class AdminRoleRead(BaseModel):
    code: str
    title: str
    permissions: list[str]


class AdminRoleListResponse(BaseModel):
    items: list[AdminRoleRead]


class AdminRouteFeedbackRead(BaseModel):
    id: int
    user_id: str
    route_id: str
    rating: int | None = None
    comment: str | None = None
    problem_types: list[str] = []
    created_at: datetime


class AdminRouteFeedbackListResponse(BaseModel):
    items: list[AdminRouteFeedbackRead]
    total: int
    limit: int
    offset: int


class AdminCoverageResponse(BaseModel):
    city_id: int
    city_slug: str
    city_name: str
    places_total: int
    places_published: int
    places_unpublished: int
    places_without_photo: int
    places_needs_recheck: int
    pending_photos: int
    route_eligible_places: int
    categories: dict[str, int]
