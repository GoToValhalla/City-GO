"""Orchestrates enrichment CSV import: preview and apply."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place_enrichment import ImportApplyResult, ImportPreviewResult
from services.place_enrichment_batch.archive import archive_batch, repair_batch_archive
from services.place_enrichment_batch.meta import read_batch_meta, update_batch_status, write_batch_meta
from services.place_enrichment_batch.paths import resolve_batch_paths
from services.place_enrichment_import.apply_changes import apply_preview
from services.place_enrichment_import.image_apply import apply_csv_images
from services.place_enrichment_import.preview_builder import build_preview


def _require_batch(batch_id: str) -> tuple[dict[str, Path], bool]:
    if read_batch_meta(batch_id) is None:
        raise FileNotFoundError(f"Batch not found: {batch_id}")
    return resolve_batch_paths(batch_id)


def _load_places(db: Session, enriched_path: Path) -> dict[int, Place]:
    import csv
    rows = list(csv.DictReader(enriched_path.read_text(encoding="utf-8").splitlines()))
    ids = [int(r["id"]) for r in rows if r.get("id", "").strip().isdigit()]
    places = db.query(Place).filter(Place.id.in_(ids)).all()
    return {p.id: p for p in places}


def _write_previewed_meta(batch_id: str, *, archived: bool) -> None:
    meta = read_batch_meta(batch_id)
    if meta is None:
        return
    updated = meta.model_copy(update={"status": "previewed", "next_action": "apply_import"})
    write_batch_meta(updated, archived=archived)


def run_import_preview(db: Session, batch_id: str) -> ImportPreviewResult:
    paths, archived = _require_batch(batch_id)
    enriched = paths["enriched_csv"]
    if not enriched.exists():
        raise FileNotFoundError(f"enriched.csv missing for batch {batch_id}")
    preview = build_preview(batch_id, enriched, _load_places(db, enriched))
    paths["import_preview"].write_text(preview.model_dump_json(indent=2), encoding="utf-8")
    if archived:
        _write_previewed_meta(batch_id, archived=True)
    else:
        update_batch_status(batch_id, "previewed", "apply_import")
    return preview


def run_import_apply(
    db: Session,
    batch_id: str,
    actor: str,
    *,
    no_archive_if_archived: bool = False,
) -> ImportApplyResult:
    paths, archived = _require_batch(batch_id)
    preview_path = paths["import_preview"]
    if not preview_path.exists():
        preview = run_import_preview(db, batch_id)
    else:
        preview = ImportPreviewResult.model_validate_json(preview_path.read_text("utf-8"))
    result = apply_preview(db, preview, actor=actor)
    image_stats = apply_csv_images(db, paths["enriched_csv"], actor=actor)
    db.commit()
    merged = {**result.model_dump(), "image_apply": image_stats}
    paths["import_result"].write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    if archived and no_archive_if_archived:
        meta = read_batch_meta(batch_id)
        if meta is not None:
            write_batch_meta(meta.model_copy(update={"status": "imported", "next_action": "archived"}), archived=True)
        return result
    update_batch_status(batch_id, "imported", "archived")
    archive_batch(batch_id)
    return result


def run_repair_archive(batch_id: str) -> str:
    """Move partial active batch artifacts into archive without DB changes."""
    return repair_batch_archive(batch_id)
