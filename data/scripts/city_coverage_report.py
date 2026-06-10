from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.import_coverage_service import build_import_coverage_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--scope", default=None)
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    with SessionLocal() as db:
        return build_import_coverage_report(db, args.city, args.scope).model_dump()


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
