from pydantic import BaseModel, Field


class RouteStartRequest(BaseModel):
    type: str = "city_center"
    lat: float | None = None
    lng: float | None = None
    label: str | None = None
    query: str | None = None
    place_id: int | None = None


class RouteWarningRead(BaseModel):
    code: str
    message: str


class RandomRouteRequest(BaseModel):
    city_slug: str
    start: RouteStartRequest | None = None
    budget_minutes: int = Field(default=120, ge=15, le=480)
    selected_category_slugs: list[str] = []
    category_mode: str = "none"
    seed: int | None = None
    session_token: str = Field(..., min_length=8, max_length=255)


class DraftPointRead(BaseModel):
    id: int
    place_id: int
    position: int
    title: str
    slug: str
    category: str | None = None
    lat: float
    lng: float
    visit_minutes: int
    open_status: str
    user_locked: bool = False
    inserted_by_user: bool = False
    replacement_of_place_id: int | None = None
    walk_minutes_from_prev: int | None = None
    walk_minutes_to_next: int | None = None


class CategorySummaryRead(BaseModel):
    requested: list[str]
    matched: dict[str, int]
    neutral_added: int
    missing: list[str]


class RouteDraftRead(BaseModel):
    draft_id: int
    version: int
    route_status: str
    total_minutes: int
    budget_minutes: int
    category_mode: str
    selected_category_slugs: list[str]
    points: list[DraftPointRead]
    warnings: list[RouteWarningRead]
    category_summary: CategorySummaryRead


class RemovePointRequest(BaseModel):
    point_id: int
    version: int


class AddPointRequest(BaseModel):
    place_id: int
    after_position: int | None = None
    version: int
    allow_readd: bool = False


class ReplacePointRequest(BaseModel):
    point_id: int
    replacement_place_id: int
    version: int


class PlaceSearchCandidateRead(BaseModel):
    place_id: int
    title: str
    category: str | None = None
    address: str | None = None
    fit_reason: str
    estimated_extra_minutes: int = 0
    score: float


class PlaceSearchResponse(BaseModel):
    items: list[PlaceSearchCandidateRead]
