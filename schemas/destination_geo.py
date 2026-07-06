"""Admin geo-search schemas for destination bootstrap."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DestinationGeoCandidateRead(BaseModel):
    candidate_key: str
    title: str
    display_name: str | None = None
    lat: float
    lng: float
    bbox: dict[str, float] | None = None
    osm_type: str | None = None
    osm_id: int | None = None
    destination_type: str
    import_strategy: str = "single_bbox"


class DestinationGeoSearchResponse(BaseModel):
    query: str
    items: list[DestinationGeoCandidateRead]


class DestinationGeoCandidateInput(BaseModel):
    candidate_key: str
    title: str
    display_name: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    bbox: dict[str, object] | None = None
    osm_type: str | None = None
    osm_id: int | None = None
    destination_type: str = "tourist_cluster"
    import_strategy: str = "single_bbox"


class AdminDestinationFromGeoCandidateRequest(BaseModel):
    candidate: DestinationGeoCandidateInput
    slug: str | None = None
    name: str | None = None
    destination_type: str | None = None


class AdminScopeFromGeoCandidateRequest(BaseModel):
    candidate: DestinationGeoCandidateInput
    code: str | None = None
    name: str | None = None
    import_profile: str = "tourist_core"
    enabled: bool = True
    recover: bool = True
