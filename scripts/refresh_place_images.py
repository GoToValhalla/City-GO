from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.scripts.image_pipeline.run import run_pipeline
from data.scripts.validate_catalog_images import validate_catalog


def refresh_images(live: bool, mapillary_token: str | None) -> dict[str, object]:
    counts = run_pipeline(live=live, mapillary_token=mapillary_token)
    errors = validate_catalog()
    return {"live": live, "counts": counts, "validation_errors": errors}


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--mapillary-token", default=None)
    args = parser.parse_args()
    print(json.dumps(refresh_images(args.live, args.mapillary_token), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
