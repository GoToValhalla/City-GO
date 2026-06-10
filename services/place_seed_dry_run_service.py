from schemas.place_seed_import_summary import PlaceSeedImportSummary
from schemas.place_seed_item import PlaceSeedItem
from services.place_seed_import_summary_service import (
    build_place_seed_import_summary,
)
from services.place_seed_validation_service import validate_place_seed_item


def run_place_seed_dry_run(items: list[PlaceSeedItem]) -> PlaceSeedImportSummary:
    """
    Выполняет dry-run проверку seed-элементов мест без записи в БД.

    Логика текущего MVP:
    - валидные элементы считаем как skipped
    - невалидные считаем как invalid
    - created / updated пока не трогаем, так как записи в БД нет
    """
    invalid = 0
    skipped = 0
    errors: list[str] = []

    for index, item in enumerate(items, start=1):
        result = validate_place_seed_item(item)

        if result.is_valid:
            skipped += 1
            continue

        invalid += 1
        slug_for_error = item.slug.strip() if item.slug and item.slug.strip() else "<empty-slug>"
        errors.append(f"item {index}: {slug_for_error} is invalid")

    return build_place_seed_import_summary(
        total=len(items),
        created=0,
        updated=0,
        skipped=skipped,
        invalid=invalid,
        errors=errors,
    )
