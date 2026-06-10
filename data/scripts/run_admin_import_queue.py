"""Cron: выполнить queued admin city import jobs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.admin_city_import_tasks import run_queued_import_jobs


if __name__ == "__main__":
    print(json.dumps({"processed": run_queued_import_jobs()}, ensure_ascii=False))
