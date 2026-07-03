from pydantic import BaseModel


class AdminCityCoverageRow(BaseModel):
    city_id: int
    city_slug: str
    city_name: str
    places_total: int
    places_published: int
    places_hidden: int
    places_verified: int
    places_unverified: int
    places_with_photo: int
    places_without_photo: int
    places_with_address: int
    places_without_address: int
    places_with_description: int
    places_without_description: int
    places_route_eligible: int
    places_not_route_eligible: int
    places_route_unknown: int = 0
    pending_photos: int
    quality_score: int
    severity: str


class AdminCoverageSummaryResponse(BaseModel):
    items: list[AdminCityCoverageRow]
    total: int
    limit: int
    offset: int
