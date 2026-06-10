"""Path helpers for place enrichment batch artifacts."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path("data/exports/place_enrichment")
ACTIVE = ROOT / "active"
ARCHIVE = ROOT / "archive"

BATCH_PREFIX = "place_enrichment"


def make_batch_id(city_slug: str, ts: datetime | None = None) -> str:
    stamp = (ts or datetime.utcnow()).strftime("%Y%m%d_%H%M%S")
    return f"{BATCH_PREFIX}_{city_slug}_{stamp}"


def batch_dir(batch_id: str, *, archived: bool = False) -> Path:
    base = ARCHIVE if archived else ACTIVE
    return base / batch_id


def batch_paths(batch_id: str, *, archived: bool = False) -> dict[str, Path]:
    root = batch_dir(batch_id, archived=archived)
    return {
        "root": root,
        "export_csv": root / "export.csv",
        "export_meta": root / "export.meta.json",
        "enriched_csv": root / "enriched.csv",
        "import_preview": root / "import.preview.json",
        "import_result": root / "import.result.json",
    }


def rel(path: Path) -> str:
    return str(path).replace("\\", "/")


FILE_KEYS = {
    "export.csv": "export_csv", "export.meta.json": "export_meta",
    "enriched.csv": "enriched_csv", "import.preview.json": "import_preview",
    "import.result.json": "import_result",
}

REQUIRED_ARCHIVE_KEYS = (
    "export_csv", "export_meta", "enriched_csv", "import_preview", "import_result",
)


def batch_files_complete(paths: dict[str, Path]) -> bool:
    return all(paths[key].exists() for key in REQUIRED_ARCHIVE_KEYS)


def resolve_batch_paths(batch_id: str) -> tuple[dict[str, Path], bool]:
    """Return batch paths; prefer complete archive/ over partial active/."""
    archived = batch_paths(batch_id, archived=True)
    if batch_files_complete(archived):
        return archived, True
    active = batch_paths(batch_id, archived=False)
    if active["export_csv"].exists():
        return active, False
    if archived["export_csv"].exists():
        return archived, True
    raise FileNotFoundError(f"Batch not found in active/ or archive/: {batch_id}")
