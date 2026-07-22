from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class TableOwnership(TypedDict):
    name: str
    owner: str
    type: str
    writer: str
    readers: list[str]


class ArchitectureManifest(TypedDict):
    version: int
    contexts: list[dict[str, object]]
    invariants: dict[str, object]
    tables: list[TableOwnership]


def load_manifest() -> ArchitectureManifest:
    path = Path(__file__).with_name("stage6_manifest.json")
    return json.loads(path.read_text(encoding="utf-8"))


ARCHITECTURE_MANIFEST = load_manifest()
