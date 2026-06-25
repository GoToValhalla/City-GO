from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.coverage_gap_service import build_coverage_summary, refresh_coverage_statuses, sync_known_missing_poi_seed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", dest="city_slug", default=None)
    parser.add_argument("--refresh", action="store_true", help="Also match registry rows to current places and source observations.")
    parser.add_argument("--summary", action="store_true", help="Print admin-style summary after sync.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    with SessionLocal() as db:
        if args.refresh:
            result = refresh_coverage_statuses(db, city_slug=args.city_slug)
        else:
            result = {"synced": sync_known_missing_poi_seed(db, city_slug=args.city_slug)}
        db.commit()

        if args.summary:
            result["coverage"] = build_coverage_summary(db, city_slug=args.city_slug, refresh=False)

        return {"status": "success", "city_slug": args.city_slug, **result}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
