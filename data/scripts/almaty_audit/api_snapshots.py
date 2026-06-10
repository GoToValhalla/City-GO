"""Снимки admin API: data-quality, readiness, dry-run."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def _get(url: str, token: str) -> dict[str, object] | list[object] | None:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc), "url": url}


def _post(url: str, token: str, body: dict[str, object]) -> dict[str, object] | None:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc), "url": url, "body": body}


def write_api_files(root: Path, base: str, slugs: tuple[str, ...]) -> list[str]:
    token = os.environ.get("ADMIN_API_TOKEN", "").strip()
    if not token:
        (root / "api_snapshots_NOT_RUN.txt").write_text("ADMIN_API_TOKEN не задан", encoding="utf-8")
        return []
    written: list[str] = []
    for slug in slugs:
        for name, path in (
            (f"data_quality_{slug}.json", f"/admin/routes/data-quality/{slug}"),
            (f"readiness_{slug}.json", f"/admin/routes/readiness/{slug}"),
        ):
            payload = _get(f"{base.rstrip('/')}{path}", token)
            fp = root / name
            fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(fp.name)
    scenarios = [
        ("dry_run_almaty_120.json", {"city_slug": slugs[0], "duration_min": 120, "interests": []}),
        ("dry_run_almaty_180.json", {"city_slug": slugs[0], "duration_min": 180, "interests": ["culture", "park", "food"]}),
        ("dry_run_almaty_240.json", {"city_slug": slugs[0], "duration_min": 240, "interests": ["attraction", "museum", "cafe"]}),
    ]
    for fname, body in scenarios:
        payload = _post(f"{base.rstrip('/')}/admin/routes/dry-run", token, body)
        fp = root / fname
        fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(fp.name)
    return written
