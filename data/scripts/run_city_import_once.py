"""Синхронный запуск admin city import для одного city_id."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.admin_city_import_job_service import ensure_import_job, run_city_import_job


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city-id", type=int, required=True)
    parser.add_argument("--actor", default="import-cli")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    with SessionLocal() as db:
        ensure_import_job(db, city_id=args.city_id)
        db.commit()
        job = run_city_import_job(db, city_id=args.city_id, actor_id=args.actor)
        return {
            "job_id": job.id,
            "city_id": job.city_id,
            "status": job.status,
            "scopes_total": job.scopes_total,
            "scopes_succeeded": job.scopes_succeeded,
            "places_found": job.places_found,
            "places_saved": job.places_saved,
            "last_error": job.last_error,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, default=str))
