"""LEGACY SEED IMPORT CLI.

Status: historical manual seed importer for early place import work.

How it worked:
- Posts local seed JSON files to `/place-seed/import/`.
- Defaults to Zelenogradsk seed files.

Current source of truth:
- admin import pipeline and city import job services;
- place discovery/import queue flows;
- audited import jobs from admin UI.

Rules:
- Do not use this as the production city import path.
- Do not use it for publication state repair or backlog processing.
- Keep only as historical seed-import helper.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_SEEDS = (
    Path("data/seeds/place_import/zelenogradsk_osm.json"),
    Path("data/seeds/place_import/zelenogradsk_editorial_walks.json"),
)


def import_seed(api_base: str, seed_path: Path, real: bool) -> dict[str, object]:
    payload = _payload(seed_path, real)
    request = Request(
        f"{api_base.rstrip('/')}/place-seed/import/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _payload(seed_path: Path, real: bool) -> dict[str, object]:
    payload = json.loads(seed_path.read_text())
    items = payload.get("items", [])
    return {"items": items, "dry_run": not real}


def _paths(values: list[str]) -> tuple[Path, ...]:
    return tuple(Path(value) for value in values) if values else DEFAULT_SEEDS


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("seed", nargs="*")
    args = parser.parse_args()
    results = tuple(import_seed(args.api_base, path, args.real) for path in _paths(args.seed))
    print(json.dumps({"real": bool(args.real), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
