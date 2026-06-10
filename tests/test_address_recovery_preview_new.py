from __future__ import annotations

import csv
from pathlib import Path

from services.place_address_recovery_preview import preview_from_review


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


def test_preview_from_review_does_not_modify_db_new(
    db_session,
    tmp_path: Path,
    place_factory,
) -> None:
    place = place_factory(slug="preview-target", title="Preview Target", address=None)
    before = place.address
    csv_path = tmp_path / "review.csv"
    _write_csv(csv_path, [{
        "place_id": str(place.id), "slug": place.slug, "title": place.title,
        "category": place.category or "cafe", "lat": "61.0", "lng": "69.0",
        "old_address": "", "proposed_address": "Тобольский тракт 1, Ханты-Мансийск",
        "source": "nominatim_reverse", "confidence": "medium", "raw_display_name": "",
        "should_apply": "True", "skip_reason": "", "comment": "",
    }])
    result = preview_from_review(db_session, csv_path)
    db_session.refresh(place)
    assert result["mode"] == "preview_from_review"
    assert result["would_apply"] >= 0
    assert place.address == before


def test_preview_skips_existing_real_address_new(
    db_session,
    tmp_path: Path,
    place_factory,
) -> None:
    existing_address = "улица Мира, 13, Ханты-Мансийск"
    place = place_factory(
        slug="preview-existing",
        title="Existing Address",
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
    result = preview_from_review(db_session, csv_path)
    assert result["skipped_existing_real_address"] == 1
    assert result["would_apply"] == 0
