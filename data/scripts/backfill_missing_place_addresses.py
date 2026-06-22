from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.place_address_backfill import run_backfill
from services.place_address_clear import clear_placeholder_addresses
from services.place_address_recovery import run_recovery_dry_run
from services.place_address_recovery_apply import apply_from_review
from services.place_address_recovery_preview import preview_from_review


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill and verify place addresses via Nominatim.")
    parser.add_argument("--city", required=True, help="City slug (required).")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--start-after-id", type=int, default=0, help="Only scan places with id greater than this value.")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default when --apply omitted).")
    parser.add_argument("--apply", action="store_true", help="Persist updates to DB.")
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Also check existing addresses. Matching addresses are marked as verified; conflicts go to review.",
    )
    parser.add_argument("--apply-from-review", metavar="CSV", help="Apply proposed_address from review CSV.")
    parser.add_argument("--preview", action="store_true", help="Preview apply-from-review without DB writes.")
    parser.add_argument("--export-review", action="store_true", help="Write review CSV/JSON to data/exports/address_recovery/.")
    parser.add_argument("--clear-placeholders", action="store_true", help="Clear placeholder addresses without geocoding.")
    parser.add_argument("--include-generic", action="store_true", help="Also recover generic venue addresses.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    if args.apply and args.export_review:
        raise SystemExit("--export-review works only with dry-run (omit --apply).")
    if args.apply and args.apply_from_review:
        raise SystemExit("Use either --apply or --apply-from-review, not both.")
    with SessionLocal() as db:
        if args.apply_from_review:
            if args.preview:
                return preview_from_review(db, args.apply_from_review)
            return apply_from_review(db, args.apply_from_review)
        if args.clear_placeholders:
            return clear_placeholder_addresses(db, city_slug=args.city, apply=bool(args.apply))
        if args.export_review:
            return run_recovery_dry_run(
                db,
                city_slug=args.city,
                limit=args.limit,
                sleep_seconds=args.sleep,
                export_review_files=True,
                include_generic=bool(args.include_generic),
            )
        return run_backfill(
            db,
            city_slug=args.city,
            limit=args.limit,
            sleep_seconds=args.sleep,
            apply=bool(args.apply),
            verify_existing=bool(args.verify_existing),
            start_after_id=int(args.start_after_id or 0),
        )


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
