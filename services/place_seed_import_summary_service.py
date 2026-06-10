from schemas.place_seed_import_summary import PlaceSeedImportSummary


def build_place_seed_import_summary(
    total: int,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    invalid: int = 0,
    errors: list[str] | None = None,
    auto_published: int = 0,
    needs_review_count: int = 0,
    rejected_count: int = 0,
) -> PlaceSeedImportSummary:
    """
    Собирает стандартную сводку по seed-импорту мест.

    Поля auto_published/needs_review_count/rejected_count — из Import Quality Gate.
    """
    return PlaceSeedImportSummary(
        total=total,
        created=created,
        updated=updated,
        skipped=skipped,
        invalid=invalid,
        errors=errors or [],
        auto_published=auto_published,
        needs_review_count=needs_review_count,
        rejected_count=rejected_count,
    )
