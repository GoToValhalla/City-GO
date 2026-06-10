"""audit_manifest.json."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from data.scripts.almaty_audit.paths import stamp


def _rows(path: Path) -> int:
    if not path.exists() or path.suffix != ".csv":
        return 0
    with path.open(encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)


def write_manifest(root: Path, notes: dict[str, str]) -> None:
    entries: list[dict[str, object]] = []
    for fp in sorted(root.rglob("*")):
        if not fp.is_file() or fp.name == "audit_manifest.json":
            continue
        rel = str(fp.relative_to(root))
        entries.append({
            "filename": rel,
            "row_count": _rows(fp) if fp.suffix == ".csv" else None,
            "generated_at": stamp(),
            "command_or_api_used": notes.get(rel, "generate_almaty_enrichment_audit"),
            "notes": notes.get(f"note:{rel}", ""),
        })
    (root / "audit_manifest.json").write_text(
        json.dumps({"files": entries, "generated_at": stamp()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
