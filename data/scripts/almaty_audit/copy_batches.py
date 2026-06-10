"""Копирование enrichment batches Алматы."""

from __future__ import annotations

import shutil
from pathlib import Path


def copy_enrichment_batches(src_root: Path, dest: Path, slugs: tuple[str, ...]) -> list[str]:
    copied: list[str] = []
    if not src_root.exists():
        (dest / "README.txt").write_text("Источник batches не найден", encoding="utf-8")
        return copied
    for zone in ("active", "archive"):
        base = src_root / zone
        if not base.is_dir():
            continue
        for batch_dir in sorted(base.iterdir()):
            if not batch_dir.is_dir():
                continue
            name = batch_dir.name.lower()
            if not any(s in name for s in slugs):
                continue
            target = dest / batch_dir.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(batch_dir, target)
            copied.append(batch_dir.name)
            readme = target / "README.txt"
            if not (target / "enriched.csv").exists():
                readme.write_text("Apply enrichment не выполнялся", encoding="utf-8")
    if not copied:
        (dest / "README.txt").write_text("Batch по Алматы не найден в active/archive", encoding="utf-8")
    return copied
