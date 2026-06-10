from schemas.place_seed_import_summary import PlaceSeedImportSummary


def test_place_seed_import_summary_defaults() -> None:
    summary = PlaceSeedImportSummary()

    assert summary.total == 0
    assert summary.created == 0
    assert summary.updated == 0
    assert summary.skipped == 0
    assert summary.invalid == 0
    assert summary.errors == []


def test_place_seed_import_summary_accepts_values() -> None:
    summary = PlaceSeedImportSummary(
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
