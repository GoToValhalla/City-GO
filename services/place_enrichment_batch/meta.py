"""Read/write enrichment batch metadata."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from schemas.place_enrichment import EnrichmentBatchMeta
from services.place_enrichment_batch.paths import ACTIVE, ARCHIVE, batch_dir, batch_paths, rel


def _meta_write_archived(batch_id: str, archived: bool | None) -> bool:
    if archived is not None:
        return archived
    return batch_dir(batch_id, archived=False).exists() is False


def write_batch_meta(meta: EnrichmentBatchMeta, *, archived: bool | None = None) -> None:
    use_archive = _meta_write_archived(meta.batch_id, archived)
    if batch_dir(meta.batch_id, archived=False).exists():
        use_archive = False
    paths = batch_paths(meta.batch_id, archived=use_archive)
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["export_meta"].write_text(meta.model_dump_json(indent=2), encoding="utf-8")


def read_batch_meta(batch_id: str) -> EnrichmentBatchMeta | None:
    for archived in (False, True):
        p = batch_paths(batch_id, archived=archived)["export_meta"]
        if not p.exists():
            continue
        try:
            return EnrichmentBatchMeta.model_validate_json(p.read_text("utf-8"))
        except Exception:
            continue
    return None


def update_batch_status(batch_id: str, status: str, next_action: str) -> EnrichmentBatchMeta:
    meta = read_batch_meta(batch_id)
    if meta is None:
        raise FileNotFoundError(f"Batch not found: {batch_id}")
    updated = meta.model_copy(update={"status": status, "next_action": next_action})
    write_batch_meta(updated)
    return updated


def build_batch_meta(
    *,
    batch_id: str,
    city_slug: str,
    limit: int,
    missing_fields: list[str],
    only_published: bool,
    only_route_eligible: bool,
    total_exported: int,
    by_city: dict[str, int],
    by_category: dict[str, int],
    breakdown: dict[str, int],
) -> EnrichmentBatchMeta:
    paths = batch_paths(batch_id)
    return EnrichmentBatchMeta(
        batch_id=batch_id,
        status="exported",
        city_slug=city_slug,
        limit=limit,
        missing_fields=missing_fields,
        only_published=only_published,
        only_route_eligible=only_route_eligible,
        export_csv_path=rel(paths["export_csv"]),
        enriched_csv_path=rel(paths["enriched_csv"]),
        import_preview_path=rel(paths["import_preview"]),
        import_result_path=rel(paths["import_result"]),
        created_at=datetime.utcnow(),
        total_exported=total_exported,
        by_city=by_city,
        by_category=by_category,
        missing_fields_breakdown=breakdown,
        next_action="chatgpt_enrich",
    )


def refresh_batch_status(meta: EnrichmentBatchMeta) -> EnrichmentBatchMeta:
    if meta.status == "imported":
        return meta
    paths = batch_paths(meta.batch_id)
    status, action = meta.status, meta.next_action
    if paths["import_result"].exists():
        status, action = "imported", "archived"
    elif paths["import_preview"].exists():
        status, action = "previewed", "apply_import"
    elif paths["enriched_csv"].exists():
        status, action = "enriched", "preview_import"
    if status != meta.status:
        updated = meta.model_copy(update={"status": status, "next_action": action})
        write_batch_meta(updated)
        return updated
    return meta


def list_batches(limit: int = 50) -> list[EnrichmentBatchMeta]:
    items: list[tuple[float, EnrichmentBatchMeta]] = []
    for base, archived in ((ACTIVE, False), (ARCHIVE, True)):
        if not base.exists():
            continue
        for d in base.iterdir():
            if not d.is_dir():
                continue
            meta_path = d / "export.meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = EnrichmentBatchMeta.model_validate_json(meta_path.read_text("utf-8"))
                if not archived:
                    meta = refresh_batch_status(meta)
                elif meta.status != "imported":
                    meta = meta.model_copy(update={"status": "imported", "next_action": "archived"})
                items.append((meta_path.stat().st_mtime, meta))
            except Exception:
                continue
    items.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in items[:limit]]
