"""
CLI: Place Enrichment Export with optional Git artifact batch structure.

Examples:
  python data/scripts/run_place_enrichment_export.py --city zelenogradsk --git-artifact
  python data/scripts/run_place_enrichment_export.py --limit 100 --missing-fields address,photo,description
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from schemas.place_enrichment import PlaceEnrichmentExportRequest
from services.place_enrichment_batch.meta import list_batches
from services.place_enrichment_service import run_enrichment_export


def _build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export places for data enrichment")
    p.add_argument("--city", default=None)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--only-published", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--only-route-eligible", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--missing-fields", default="address,photo,description")
    p.add_argument("--git-artifact", action="store_true", default=True)
    p.add_argument("--no-git-artifact", action="store_false", dest="git_artifact")
    return p.parse_args()


def _city_slugs(db, city: str | None) -> list[str]:
    if city:
        return [city]
    from models.city import City
    return [r.slug for r in db.query(City.slug).all()]


def _export_city(db, city_slug: str, args: argparse.Namespace) -> None:
    fields = [f.strip() for f in args.missing_fields.split(",") if f.strip()]
    req = PlaceEnrichmentExportRequest(
        city_slug=city_slug, limit=args.limit,
        only_published=args.only_published, only_route_eligible=args.only_route_eligible,
        missing_fields=fields, git_artifact=args.git_artifact,
    )
    meta = run_enrichment_export(db, req, actor="script:run_place_enrichment_export")
    if args.git_artifact and meta.batch_id:
        print(f"BATCH_ID={meta.batch_id}")
        print(f"EXPORT_CSV_PATH={meta.export_csv_path}")
        print(f"EXPORT_META_PATH=data/exports/place_enrichment/active/{meta.batch_id}/export.meta.json")
        print("NEXT_ACTION=commit_and_send_path_to_chatgpt")
    print(f"  total_exported: {meta.total_exported}")


def main() -> None:
    args = _build_args()
    db = SessionLocal()
    try:
        slugs = _city_slugs(db, args.city)
        if not slugs:
            print("No cities found.")
            return
        for slug in slugs:
            print(f"\n[{slug}]")
            _export_city(db, slug, args)
        print(f"\nDone. Batches in storage: {len(list_batches())}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
