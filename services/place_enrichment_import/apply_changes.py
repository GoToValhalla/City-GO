"""Apply enrichment import changes to Place records."""
from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place_enrichment import ImportApplyResult, ImportPreviewResult
from services.admin_audit_service import write_admin_audit_log


def apply_preview(
    db: Session,
    preview: ImportPreviewResult,
    *,
    actor: str,
) -> ImportApplyResult:
    fields_updated: dict[str, int] = {}
    errors = list(preview.errors)
    rows_updated = 0

    for row in preview.changes:
        place = db.query(Place).filter(Place.id == row.place_id).first()
        if place is None:
            errors.append(f"Place not found id={row.place_id}")
            continue
        changed = False
        for upd in row.updates:
            setattr(place, upd.field, upd.new_value)
            fields_updated[upd.field] = fields_updated.get(upd.field, 0) + 1
            changed = True
        if changed:
            rows_updated += 1

    write_admin_audit_log(
        db, actor=actor, action="place_enrichment_import",
        entity_type="place_enrichment_batch", entity_id=preview.batch_id,
        new_value={
            "rows_updated": rows_updated,
            "fields_updated": fields_updated,
            "skipped_unsupported_fields": preview.unsupported_fields,
        },
    )
    db.commit()
    return ImportApplyResult(
        batch_id=preview.batch_id,
        rows_updated=rows_updated,
        fields_updated=fields_updated,
        skipped_unsupported_fields=preview.unsupported_fields,
        errors=errors,
    )
