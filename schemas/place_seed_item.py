from datetime import datetime

from pydantic import BaseModel, Field

from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


class PlaceSeedItem(BaseModel):
    """
    Каноничный seed-элемент места.

    Это подготовка под:
    - seed import
    - bulk validation
    - AI enrichment pipeline
    """

    title: str
    slug: str
    city_slug: str
    category: str
    address: str | None = None
    short_description: str | None = None
    taxonomy: PlaceTaxonomyPayload
    source: str | None = None
    source_url: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    last_verified_at: datetime | None = None
    status: str = "active"
    lat: float | None = None
    lng: float | None = None
    opening_hours: dict[str, object] | None = None
    average_visit_duration_minutes: int | None = Field(default=None, ge=1, le=600)
    price_level: int | None = Field(default=None, ge=0, le=3)
    is_active: bool = True
