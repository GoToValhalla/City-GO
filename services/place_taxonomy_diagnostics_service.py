from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from services.place_taxonomy_diagnostics_response_service import (
    build_place_taxonomy_diagnostics_response,
)
from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
)


def get_invalid_place_taxonomy_values(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Возвращает невалидные значения таксономии места.

    Нужен для:
    - импорта seed-данных
    - админских проверок
    - AI enrichment pipeline
    - отладки перед записью в БД
    """
    invalid_category = None if is_valid_place_category(payload.category) else payload.category

    invalid_tags = [value for value in payload.tags if not is_valid_place_tag(value)]
    invalid_scenario_tags = [
        value for value in payload.scenario_tags if not is_valid_place_scenario_tag(value)
    ]
    invalid_vibe_tags = [
        value for value in payload.vibe_tags if not is_valid_place_vibe_tag(value)
    ]
    invalid_restriction_tags = [
        value
        for value in payload.restriction_tags
        if not is_valid_place_restriction_tag(value)
    ]

    return build_place_taxonomy_diagnostics_response(
        category=invalid_category,
        tags=invalid_tags,
        scenario_tags=invalid_scenario_tags,
        vibe_tags=invalid_vibe_tags,
        restriction_tags=invalid_restriction_tags,
    )