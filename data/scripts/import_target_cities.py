from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts.run_due_import_jobs import run as run_due_import_jobs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="data/config/import_targets.json")
    parser.add_argument("--city", action="append")
    parser.add_argument("--scope", action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")
    forwarded = [
        "--config", args.config,
        *[item for city in args.city or [] for item in ("--city", city)],
        *[item for scope in args.scope or [] for item in ("--scope", scope)],
        "--force",
        "--apply" if args.apply else "--dry-run",
    ]
    return run_due_import_jobs(forwarded)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
