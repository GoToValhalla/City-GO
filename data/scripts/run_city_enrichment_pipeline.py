"""CLI: обогащение существующего города без OSM re-import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from services.admin_city_import_job_service import ensure_import_job, run_enrichment_only_job
from services.city_slug_resolver import resolve_city_by_slug


def main(argv: list[str] | None = None) -> dict[str, object]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--actor", default="pipeline-cli")
    parser.add_argument("--address-limit", type=int, default=None)
    parser.add_argument("--image-limit", type=int, default=None)
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        city = resolve_city_by_slug(db, args.city)
        if city is None:
            raise SystemExit(f"City not found: {args.city}")
        job = ensure_import_job(db, city_id=city.id)
        db.commit()
        if args.address_limit:
            import services.import_pipeline.enrichment_only as eo
            eo.ADDRESS_LIMIT = args.address_limit
        if args.image_limit:
            import services.import_pipeline.enrichment_only as eo
            eo.IMAGE_LIMIT = args.image_limit
        finished = run_enrichment_only_job(db, city_id=city.id, actor_id=args.actor)
        return {"job_id": finished.id, "status": finished.status, "current_step": finished.current_step}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2, default=str))
