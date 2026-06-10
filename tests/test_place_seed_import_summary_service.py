from services.place_seed_import_summary_service import (
    build_place_seed_import_summary,
)


def test_build_place_seed_import_summary_defaults_errors_to_empty_list() -> None:
    summary = build_place_seed_import_summary(total=5)

    assert summary.total == 5
    assert summary.created == 0
    assert summary.updated == 0
    assert summary.skipped == 0
    assert summary.invalid == 0
    assert summary.errors == []


def test_build_place_seed_import_summary_accepts_all_values() -> None:
    summary = build_place_seed_import_summary(
        total=10,
        created=4,
        updated=3,
        skipped=2,
        invalid=1,
        errors=["row 7 invalid"],
    )

    assert summary.total == 10
    assert summary.created == 4
    assert summary.updated == 3
    assert summary.skipped == 2
    assert summary.invalid == 1
    assert summary.errors == ["row 7 invalid"]
