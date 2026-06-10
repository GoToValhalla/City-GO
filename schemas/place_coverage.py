from pydantic import BaseModel, Field


class PlaceCoverageReport(BaseModel):
    city_slug: str
    total_places: int = 0
    with_coordinates: int = 0
    with_opening_hours: int = 0
    with_visit_duration: int = 0
    with_source: int = 0
    active_places: int = 0
    needs_verification: int = 0
    temporarily_closed_places: int = 0
    closed_places: int = 0
    average_confidence: float | None = None
    # Address & photo coverage
    with_address: int = 0
    without_address: int = 0
    with_photo: int = 0
    without_photo: int = 0
    # Verification & routing
    verified: int = 0
    route_eligible: int = 0
    # Publication breakdown (published / needs_review / hidden / draft)
    publication_status_breakdown: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    route_features: list[str] = Field(default_factory=list)
    missing_required_categories: list[str] = Field(default_factory=list)
    route_ready_score: float = 0.0
