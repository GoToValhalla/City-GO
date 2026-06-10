"""CLI: снимки всех городов из import_targets для audit run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts.full_city_snapshot_metrics import snapshot_all_cities
from data.scripts.import_cron_config import load_targets, merge_import_targets, DEFAULT_TARGET_FILE
from data.scripts.import_cron_config import load_db_targets
from db.session import SessionLocal


def city_slugs(config: Path) -> list[str]:
    json_targets = load_targets(config)
    with SessionLocal() as db:
        merged = merge_import_targets(json_targets, load_db_targets(db))
    return sorted({str(item["city"]) for item in merged})


def run(config: Path) -> dict[str, object]:
    slugs = city_slugs(config)
    with SessionLocal() as db:
        items = snapshot_all_cities(db, slugs)
    return {"city_count": len(slugs), "city_slugs": slugs, "cities": items}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_TARGET_FILE))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    payload = run(Path(args.config))
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
