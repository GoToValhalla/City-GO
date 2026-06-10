"""Move and repair enrichment batches between active and archive."""
from __future__ import annotations

import shutil

from schemas.place_enrichment import EnrichmentBatchMeta
from services.place_enrichment_batch.meta import read_batch_meta, write_batch_meta
from services.place_enrichment_batch.paths import (
    ARCHIVE,
    REQUIRED_ARCHIVE_KEYS,
    batch_dir,
    batch_files_complete,
    batch_paths,
    rel,
)


class ArchiveIncompleteError(RuntimeError):
    """Raised when archive directory is missing required batch artifacts."""


def _relocated_meta(batch_id: str) -> EnrichmentBatchMeta:
    meta = read_batch_meta(batch_id)
    if meta is None:
        raise FileNotFoundError(f"Batch meta missing: {batch_id}")
    paths = batch_paths(batch_id, archived=True)
    return meta.model_copy(update={
        "status": "imported",
        "next_action": "archived",
        "export_csv_path": rel(paths["export_csv"]),
        "enriched_csv_path": rel(paths["enriched_csv"]),
        "import_preview_path": rel(paths["import_preview"]),
        "import_result_path": rel(paths["import_result"]),
    })


def _move_artifact(src, dst) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    shutil.move(str(src), str(dst))


def _remove_active_root(active_root) -> None:
    if not active_root.exists():
        return
    leftovers = list(active_root.iterdir())
    if leftovers:
        raise ArchiveIncompleteError(f"Active batch not empty: {active_root}")
    active_root.rmdir()


def _transfer_artifacts(active: dict, archived: dict) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archived["root"].mkdir(parents=True, exist_ok=True)
    for key in REQUIRED_ARCHIVE_KEYS:
        _move_artifact(active[key], archived[key])


def archive_batch(batch_id: str) -> str:
    active = batch_paths(batch_id, archived=False)
    archived = batch_paths(batch_id, archived=True)
    if not active["root"].exists():
        if batch_files_complete(archived):
            return str(archived["root"])
        raise FileNotFoundError(f"Active batch not found: {batch_id}")
    if not batch_files_complete(active):
        raise ArchiveIncompleteError(f"Incomplete active batch: {batch_id}")
    _transfer_artifacts(active, archived)
    _remove_active_root(active["root"])
    write_batch_meta(_relocated_meta(batch_id), archived=True)
    if active["root"].exists() or not batch_files_complete(archived):
        raise ArchiveIncompleteError(f"Archive incomplete for batch: {batch_id}")
    return str(archived["root"])


def repair_batch_archive(batch_id: str) -> str:
    active = batch_paths(batch_id, archived=False)
    archived = batch_paths(batch_id, archived=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archived["root"].mkdir(parents=True, exist_ok=True)
    for key in REQUIRED_ARCHIVE_KEYS:
        src, dst = active[key], archived[key]
        if not src.exists():
            continue
        if dst.exists():
            src.unlink()
            continue
        _move_artifact(src, dst)
    if active["root"].exists():
        if any(active["root"].iterdir()):
            shutil.rmtree(active["root"])
        else:
            _remove_active_root(active["root"])
    if read_batch_meta(batch_id) is not None:
        write_batch_meta(_relocated_meta(batch_id), archived=True)
    if batch_dir(batch_id, archived=False).exists() or not batch_files_complete(archived):
        raise ArchiveIncompleteError(f"Repair failed for batch: {batch_id}")
    return str(archived["root"])
