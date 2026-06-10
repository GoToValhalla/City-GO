from core.place_taxonomy import (
    PLACE_CATEGORIES,
    PLACE_RESTRICTION_TAGS,
    PLACE_SCENARIO_TAGS,
    PLACE_TAGS,
    PLACE_VIBE_TAGS,
    USER_SIGNALS,
)
from schemas.place_taxonomy_response import PlaceTaxonomyResponse


def build_place_taxonomy_response() -> PlaceTaxonomyResponse:
    """
    Собирает стандартный ответ для каноничной таксономии City GO.
    """
    return PlaceTaxonomyResponse(
        categories=PLACE_CATEGORIES,
        tags=PLACE_TAGS,
        scenario_tags=PLACE_SCENARIO_TAGS,
        vibe_tags=PLACE_VIBE_TAGS,
        restriction_tags=PLACE_RESTRICTION_TAGS,
        user_signals=USER_SIGNALS,
    )
