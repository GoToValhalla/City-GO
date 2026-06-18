#!/usr/bin/env python
"""Recalculate Data Foundation quality scores and city readiness snapshots.

Usage:
    python scripts/recalculate_city_readiness.py --city zelenogradsk
    python scripts/recalculate_city_readiness.py --all
    python scripts/recalculate_city_readiness.py --all --skip-place-scores
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from db.session import SessionLocal
from services.city_readiness import (
    recalculate_all_city_readiness_snapshots,
    recalculate_city_readiness_snapshot,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recalculate city readiness snapshots")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--city", dest="city_slug", help="City slug to recalculate")
    scope.add_argument("--all", action="store_true", help="Recalculate all cities")
    parser.add_argument(
        "--skip-place-scores",
        action="store_true",
        help="Only rebuild city snapshots; do not recalculate per-place quality scores",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional city limit for --all")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        if args.all:
            payload: object = recalculate_all_city_readiness_snapshots(
                db,
                reason="script_city_readiness_recalculation",
                recalculate_place_scores=not args.skip_place_scores,
                limit=args.limit,
            )
        else:
            payload = recalculate_city_readiness_snapshot(
                db,
                city_slug=args.city_slug,
                reason="script_city_readiness_recalculation",
                recalculate_place_scores=not args.skip_place_scores,
            )
            if payload is None:
                print(json.dumps({"status": "error", "error": "city_not_found", "city_slug": args.city_slug}, ensure_ascii=False))
                return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
