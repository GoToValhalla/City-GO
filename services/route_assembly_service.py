from typing import Any

from schemas.merged_context import MergedContext
from services.scoring_service import ScoredPlace
from services.route_assembly_optimizer import assemble_route


class RoutePoint:
    def __init__(
        self,
        place_id: str,
        lat: float,
        lng: float,
        score: float,
        category: str,
        visit_minutes: int,
        opening_hours: dict | None = None,
        validation: dict[str, Any] | None = None,
        price_level: int | None = None,
        scoring_breakdown: dict[str, float] | None = None,
        title: str | None = None,
        address: str | None = None,
        image_url: str | None = None,
        short_description: str | None = None,
        source: str | None = None,
        city_slug: str | None = None,
    ):
        self.place_id = place_id
        self.city_slug = city_slug
        self.title = title
        self.address = address
        self.image_url = image_url
        self.short_description = short_description
        self.source = source
        self.lat = lat
        self.lng = lng
        self.score = score
        self.category = category
        self.visit_minutes = visit_minutes
        self.opening_hours = opening_hours
        # Снимок validate_place(place) с ORM Place (после retrieval); нужен finalize / explainability downstream.
        self.validation = validation
        self.price_level = price_level
        self.scoring_breakdown = dict(scoring_breakdown or {})


class RouteAssemblyService:
    """Adapter around pure assembly optimizer."""

    def build(self, scored: list[ScoredPlace], ctx: MergedContext) -> list[RoutePoint]:
        return assemble_route(scored, ctx, RoutePoint)
