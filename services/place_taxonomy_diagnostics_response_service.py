from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def build_place_taxonomy_diagnostics_response(
    category: str | None,
    tags: list[str],
    scenario_tags: list[str],
    vibe_tags: list[str],
    restriction_tags: list[str],
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Собирает стандартный ответ диагностики taxonomy payload.
    """
    return PlaceTaxonomyDiagnosticsResponse(
        category=category,
        tags=tags,
        scenario_tags=scenario_tags,
        vibe_tags=vibe_tags,
        restriction_tags=restriction_tags,
    )
