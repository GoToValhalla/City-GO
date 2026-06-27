"""Orchestrates enrichment export: query → CSV → batch artifacts → audit."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from models.city import City
from schemas.place_enrichment import EnrichmentBatchMeta, EnrichmentExportMeta, PlaceEnrichmentExportRequest
from services.admin_audit_service import write_admin_audit_log
from services.place_enrichment_batch.meta import build_batch_meta, list_batches, read_batch_meta, write_batch_meta
from services.place_enrichment_batch.paths import FILE_KEYS, ROOT, batch_paths, make_batch_id
from services.place_enrichment_csv import build_csv
from services.place_enrichment_query import missing_fields_breakdown, query_places_for_enrichment

EXPORTS_DIR = ROOT


def _export_to_batch(
    db: Session, req: PlaceEnrichmentExportRequest, actor: str, city_name: str, places: list,
) -> EnrichmentExportMeta:
    batch_id = make_batch_id(req.city_slug)
    paths = batch_paths(batch_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["export_csv"].write_text(build_csv(places, req.city_slug, city_name), encoding="utf-8")

    by_category = dict(Counter(p.category or "unknown" for p in places))
    breakdown = missing_fields_breakdown(places, req.missing_fields)
    batch_meta = build_batch_meta(
        batch_id=batch_id, city_slug=req.city_slug, limit=req.limit,
        missing_fields=req.missing_fields, only_published=req.only_published,
        only_route_eligible=req.only_route_eligible, total_exported=len(places),
        by_city={req.city_slug: len(places)}, by_category=by_category, breakdown=breakdown,
    )
    write_batch_meta(batch_meta)
    write_admin_audit_log(
        db, actor=actor, action="place_enrichment_export",
        entity_type="place_enrichment_batch", entity_id=batch_id,
        new_value={
            "city_slug": req.city_slug,
            "limit": req.limit,
            "missing_fields": req.missing_fields,
            "only_published": req.only_published,
            "only_unpublished": req.only_unpublished,
            "total_exported": len(places),
        },
    )
    db.commit()
    return _batch_to_export_meta(batch_meta)


def _batch_to_export_meta(batch: EnrichmentBatchMeta) -> EnrichmentExportMeta:
    return EnrichmentExportMeta(
        export_id=batch.batch_id, batch_id=batch.batch_id, status=batch.status,
        file_path=batch.export_csv_path, export_csv_path=batch.export_csv_path,
        enriched_csv_path=batch.enriched_csv_path, city_slug=batch.city_slug,
        total_exported=batch.total_exported, by_city=batch.by_city,
        by_category=batch.by_category,
        missing_fields_breakdown=batch.missing_fields_breakdown,
        created_at=batch.created_at, next_action=batch.next_action,
    )


def run_enrichment_export(
    db: Session, req: PlaceEnrichmentExportRequest, actor: str,
) -> EnrichmentExportMeta:
    city = db.query(City).filter(City.slug == req.city_slug).first()
    city_name = city.name if city else req.city_slug
    places = query_places_for_enrichment(
        db, city_slug=req.city_slug, limit=req.limit,
        only_published=req.only_published, only_unpublished=req.only_unpublished,
        only_route_eligible=req.only_route_eligible,
        missing_fields=req.missing_fields,
    )
    # Legacy flat exports were removed; keep the public contract compatible by
    # always returning a batch artifact even when older clients send git_artifact=false.
    return _export_to_batch(db, req, actor, city_name, places)


def list_enrichment_exports(limit: int = 50) -> list[EnrichmentExportMeta]:
    return [_batch_to_export_meta(b) for b in list_batches(limit)]


def list_enrichment_batches(limit: int = 50) -> list[EnrichmentBatchMeta]:
    return list_batches(limit)


def get_batch_file_path(batch_id: str, filename: str) -> Path | None:
    for archived in (False, True):
        paths = batch_paths(batch_id, archived=archived)
        key = FILE_KEYS.get(filename)
        candidate = paths[key] if key else paths["root"] / filename
        if candidate.exists():
            return candidate
    return None


def get_export_csv_path(export_id: str) -> Path | None:
    meta = read_batch_meta(export_id)
    if meta:
        p = Path(meta.export_csv_path)
        return p if p.exists() else None
    legacy = EXPORTS_DIR / f"{export_id}.csv"
    return legacy if legacy.exists() else None