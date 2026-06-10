from schemas.place_seed_item import PlaceSeedItem
from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)


def validate_place_seed_item(item: PlaceSeedItem) -> PlaceSeedValidationResponse:
    """
    Валидирует один seed-элемент места.

    Сейчас проверяем:
    - обязательные текстовые поля не пустые
    - taxonomy проходит каноничную диагностику

    Позже сюда можно добавить:
    - проверку city_slug по БД
    - проверку уникальности slug
    - проверку lat/lng pair
    - проверку source/source_url
    """
    errors: list[str] = []

    if not item.title.strip():
        errors.append("title is empty")

    if not item.slug.strip():
        errors.append("slug is empty")

    if not item.city_slug.strip():
        errors.append("city_slug is empty")

    taxonomy_diagnostics = get_invalid_place_taxonomy_values(item.taxonomy)

    has_invalid_taxonomy = any(
        [
            taxonomy_diagnostics.category is not None,
            len(taxonomy_diagnostics.tags) > 0,
            len(taxonomy_diagnostics.scenario_tags) > 0,
            len(taxonomy_diagnostics.vibe_tags) > 0,
            len(taxonomy_diagnostics.restriction_tags) > 0,
        ]
    )

    is_valid = len(errors) == 0 and not has_invalid_taxonomy

    return PlaceSeedValidationResponse(
        is_valid=is_valid,
        title=item.title,
        slug=item.slug,
        city_slug=item.city_slug,
        taxonomy_diagnostics=taxonomy_diagnostics,
        errors=errors,
    )
