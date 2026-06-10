from __future__ import annotations

import csv
from pathlib import Path

from services.place_address_recovery_apply import apply_from_review


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "place_id", "slug", "title", "category", "lat", "lng", "old_address",
        "proposed_address", "source", "confidence", "raw_display_name",
        "should_apply", "skip_reason", "comment",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_apply_from_review_updates_only_should_apply_true_new(
    db_session,
    tmp_path: Path,
    place_factory,
) -> None:
    target = place_factory(slug="apply-target", title="Target Place", address=None)
    skip_place = place_factory(slug="skip-me", title="Стелла", category="culture", address=None)
    csv_path = tmp_path / "review.csv"
    _write_csv(csv_path, [
        {
            "place_id": str(target.id), "slug": target.slug, "title": target.title,
            "category": target.category or "cafe", "lat": "61.0", "lng": "69.0",
            "old_address": "", "proposed_address": "Тобольский тракт 1, Ханты-Мансийск",
            "source": "nominatim_reverse", "confidence": "medium", "raw_display_name": "",
            "should_apply": "True", "skip_reason": "", "comment": "",
        },
        {
            "place_id": str(skip_place.id), "slug": skip_place.slug, "title": skip_place.title,
            "category": skip_place.category or "culture", "lat": "61.0", "lng": "69.0",
            "old_address": "", "proposed_address": "Тобольский тракт, Ханты-Мансийск",
            "source": "nominatim_reverse", "confidence": "medium-low", "raw_display_name": "",
            "should_apply": "False", "skip_reason": "manual", "comment": "",
        },
    ])
    result = apply_from_review(db_session, csv_path)
    db_session.refresh(target)
    assert result["applied"] == 1
    assert result["skipped_should_apply_false"] == 1
    assert target.address == "Тобольский тракт 1, Ханты-Мансийск"


def test_apply_from_review_does_not_overwrite_existing_address_new(
    db_session,
    tmp_path: Path,
    place_factory,
) -> None:
    existing_address = "улица Мира, 13, Ханты-Мансийск"
    place = place_factory(
        slug="existing-address",
        title="Existing Address Place",
        category="food",
        address=existing_address,
    )
    csv_path = tmp_path / "review.csv"
    _write_csv(csv_path, [{
        "place_id": str(place.id), "slug": place.slug, "title": place.title,
        "category": place.category or "food", "lat": "61.0", "lng": "69.0",
        "old_address": "", "proposed_address": "Новый адрес 999",
        "source": "nominatim_reverse", "confidence": "medium", "raw_display_name": "",
        "should_apply": "True", "skip_reason": "", "comment": "",
    }])
    result = apply_from_review(db_session, csv_path)
    db_session.refresh(place)
    assert result["skipped_existing_real_address"] == 1
    assert place.address == existing_address


def test_apply_from_review_skips_city_only_new(db_session, tmp_path: Path) -> None:
    csv_path = tmp_path / "review.csv"
    _write_csv(csv_path, [{
        "place_id": "999999", "slug": "missing", "title": "Иртыш", "category": "walk",
        "lat": "61.0", "lng": "69.0", "old_address": "", "proposed_address": "Ханты-Мансийск",
        "source": "nominatim_reverse", "confidence": "none", "raw_display_name": "",
        "should_apply": "True", "skip_reason": "", "comment": "",
    }])
    result = apply_from_review(db_session, csv_path)
    assert result["applied"] == 0
    assert result["skipped_policy"] == 1
