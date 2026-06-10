from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.place_address_flow import run_address_recovery_flow


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatic address recovery flow.")
    parser.add_argument("--all-cities", action="store_true", help="Process all cities in DB.")
    parser.add_argument("--city", action="append", dest="cities", help="City slug (repeatable).")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default).")
    parser.add_argument("--apply", action="store_true", help="Apply should_apply rows from review CSV.")
    parser.add_argument("--no-apply", action="store_true", help="Report only, never write DB.")
    parser.add_argument("--include-generic", action="store_true", help="Include generic venue addresses.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    if not args.all_cities and not args.cities:
        raise SystemExit("Specify --all-cities or --city <slug>.")
    if args.apply and args.no_apply:
        raise SystemExit("Use either --apply or --no-apply, not both.")
    apply_changes = bool(args.apply) and not args.no_apply
    city_slugs = None if args.all_cities else list(args.cities or [])
    with SessionLocal() as db:
        return run_address_recovery_flow(
            db,
            city_slugs=city_slugs,
            limit=args.limit,
            sleep_seconds=args.sleep,
            apply_changes=apply_changes,
            include_generic=bool(args.include_generic),
        )


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
