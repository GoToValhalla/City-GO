"""Build import preview from enriched CSV rows."""
from __future__ import annotations

import csv
from pathlib import Path

from models.place import Place
from schemas.place_enrichment import ImportFieldUpdate, ImportPreviewResult, ImportRowPreview
from services.place_enrichment_import.field_map import IMAGE_PIPELINE, IMPORTABLE, UNSUPPORTED
from services.place_enrichment_import.parse_values import is_empty, parse_field


def _current_value(place: Place, field: str) -> object:
    return getattr(place, field, None)


def _values_equal(old: object, new: object) -> bool:
    if old is None and new in ("", None):
        return True
    return str(old) == str(new)


def build_preview(batch_id: str, enriched_path: Path, places: dict[int, Place]) -> ImportPreviewResult:
    rows = list(csv.DictReader(enriched_path.read_text(encoding="utf-8").splitlines()))
    changes: list[ImportRowPreview] = []
    skipped_rows: list[dict[str, object]] = []
    unsupported: dict[str, int] = {}
    errors: list[str] = []

    for row in rows:
        pid_raw = row.get("id", "").strip()
        slug = row.get("slug", "").strip()
        if not pid_raw.isdigit():
            errors.append(f"Invalid id in row slug={slug}")
            continue
        place_id = int(pid_raw)
        place = places.get(place_id)
        if place is None:
            skipped_rows.append({"place_id": place_id, "slug": slug, "reason": "not_found"})
            continue
        if slug and place.slug != slug:
            errors.append(f"Slug mismatch id={place_id}: csv={slug} db={place.slug}")
            continue

        updates: list[ImportFieldUpdate] = []
        row_skipped: list[str] = []
        for col, val in row.items():
            if not col.startswith("suggested_") or is_empty(val):
                continue
            if col in IMAGE_PIPELINE:
                row_skipped.append("pending_image_apply_on_import")
                unsupported[col] = unsupported.get(col, 0) + 1
                continue
            if col in UNSUPPORTED:
                row_skipped.append("skipped_unsupported_field")
                unsupported[col] = unsupported.get(col, 0) + 1
                continue
            db_field = IMPORTABLE.get(col)
            if not db_field:
                unsupported[col] = unsupported.get(col, 0) + 1
                continue
            new_val = parse_field(col, val)
            if new_val is None:
                continue
            old_val = _current_value(place, db_field)
            if _values_equal(old_val, new_val):
                continue
            updates.append(ImportFieldUpdate(
                field=db_field, old_value=old_val, new_value=new_val, source_column=col,
            ))

        if updates:
            changes.append(ImportRowPreview(
                place_id=place_id, slug=place.slug, title=place.title,
                updates=updates, skipped=sorted(set(row_skipped)),
            ))

    return ImportPreviewResult(
        batch_id=batch_id, total_rows=len(rows), rows_with_changes=len(changes),
        changes=changes, skipped_rows=skipped_rows,
        unsupported_fields=unsupported, errors=errors,
    )
