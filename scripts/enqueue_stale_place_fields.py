from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.session import SessionLocal
from services.place_freshness_service import enqueue_stale_place_fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue stale critical place fields for admin review.")
    parser.add_argument("--city", default=None, help="Optional city slug")
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = enqueue_stale_place_fields(db, city_slug=args.city)
    print(json.dumps(summary, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
