"""
CLI: Import enriched CSV back into Place records.

Preview:
  python data/scripts/import_place_enrichment_csv.py --batch-id <id> --preview
Apply:
  python data/scripts/import_place_enrichment_csv.py --batch-id <id> --apply
Apply archived batch (server re-apply):
  python data/scripts/import_place_enrichment_csv.py --batch-id <id> --apply --no-archive-if-archived
Repair archive (no DB):
  python data/scripts/import_place_enrichment_csv.py --batch-id <id> --repair-archive
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.place_enrichment_import_service import (
    run_import_apply,
    run_import_preview,
    run_repair_archive,
)


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import enriched place CSV")
    p.add_argument("--batch-id", required=True)
    p.add_argument("--no-archive-if-archived", action="store_true")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--repair-archive", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _args()
    if args.repair_archive:
        path = run_repair_archive(args.batch_id)
        print(json.dumps({"batch_id": args.batch_id, "archive_path": path}, ensure_ascii=False))
        return
    db = SessionLocal()
    try:
        if args.preview:
            result = run_import_preview(db, args.batch_id)
            print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str))
        else:
            result = run_import_apply(
                db, args.batch_id,
                actor="script:import_place_enrichment_csv",
                no_archive_if_archived=args.no_archive_if_archived,
            )
            print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
