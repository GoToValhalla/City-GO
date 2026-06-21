"""Cron: выполнить queued admin city import jobs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.admin_city_import_tasks import run_queued_import_jobs


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run queued admin city import jobs.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("IMPORT_WORKER_BATCH_LIMIT", "1")))
    parser.add_argument("--actor", default=os.getenv("IMPORT_WORKER_ACTOR", "import-worker"))
    return parser.parse_args()


if __name__ == "__main__":
    args = _args()
    print(json.dumps(run_queued_import_jobs(actor_id=args.actor, limit=args.limit), ensure_ascii=False, default=str))
