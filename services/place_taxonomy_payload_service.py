from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
    validate_tag_list,
)


def normalize_place_taxonomy_payload(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyPayload:
    """
    Нормализует и очищает таксономию места по каноничным правилам.

    Правила:
    - category оставляем только если она валидна
    - tags / scenario_tags / vibe_tags / restriction_tags
      очищаем от невалидных значений и дублей
    """
    category = payload.category if is_valid_place_category(payload.category) else ""

    return PlaceTaxonomyPayload(
        category=category,
        tags=validate_tag_list(payload.tags, is_valid_place_tag),
        scenario_tags=validate_tag_list(
            payload.scenario_tags,
            is_valid_place_scenario_tag,
        ),
        vibe_tags=validate_tag_list(payload.vibe_tags, is_valid_place_vibe_tag),
        restriction_tags=validate_tag_list(
            payload.restriction_tags,
            is_valid_place_restriction_tag,
        ),
    )
