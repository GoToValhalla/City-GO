from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup
from data.scripts.enrich_place_images import run as run_image_enrichment
from data.scripts.import_city_osm_v2 import run as run_osm_import
from db.session import SessionLocal
from data.scripts.import_cron_config import (
    DEFAULT_TARGET_FILE,
    load_db_targets,
    load_targets,
    merge_import_targets,
    select_targets,
    split_csv,
)
from data.scripts.import_cron_db import lock_target, schedule_next, unlock_target

DEFAULT_ADDRESS_BACKFILL_LIMIT = 5000
DEFAULT_ADDRESS_BACKFILL_SLEEP_SECONDS = 1.1
DEFAULT_IMAGE_ENRICHMENT_LIMIT = 2000
MIN_SAVED_BEFORE_BBOX_FALLBACK = 3
BBOX_FALLBACK_EXPANSION_FACTOR = 1.8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_TARGET_FILE))
    parser.add_argument("--city", action="append")
    parser.add_argument("--scope", action="append")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-address-backfill", action="store_true")
    parser.add_argument("--skip-image-enrichment", action="store_true")
    parser.add_argument("--skip-quality-cleanup", action="store_true")
    parser.add_argument("--address-backfill-limit", type=int, default=DEFAULT_ADDRESS_BACKFILL_LIMIT)
    parser.add_argument("--address-backfill-sleep", type=float, default=DEFAULT_ADDRESS_BACKFILL_SLEEP_SECONDS)
    parser.add_argument("--image-enrichment-limit", type=int, default=DEFAULT_IMAGE_ENRICHMENT_LIMIT)
    parser.add_argument("--city-admin-import-job-id", type=int, default=None)
    return parser.parse_args(argv)


def run(argv: list[str] | None = None, now: datetime | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    current = now or datetime.utcnow()

    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    targets = _targets(args)
    if args.city_admin_import_job_id is not None:
        targets = [{**target, "city_admin_import_job_id": args.city_admin_import_job_id} for target in targets]
    results = [_run_target(target, args, current) for target in targets]

    return {
        "started_at": current.isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "target_count": len(targets),
        "pipeline_order": [
            "osm_import",
            "address_backfill",
            "image_enrichment",
            "quality_cleanup",
        ],
        "address_backfill_limit": args.address_backfill_limit,
        "address_backfill_sleep": args.address_backfill_sleep,
        "image_enrichment_limit": args.image_enrichment_limit,
        "results": results,
    }


def _targets(args: argparse.Namespace) -> list[dict[str, Any]]:
    json_targets = load_targets(Path(args.config))
    with SessionLocal() as db:
        db_targets = load_db_targets(db)
    targets = merge_import_targets(json_targets, db_targets)
    selected = select_targets(targets, split_csv(args.city), split_csv(args.scope))

    if not selected:
        raise SystemExit("No configured import targets match filters")

    return selected


def _run_target(target: dict[str, Any], args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    locked_scope = lock_target(target, now, args.force)

    if locked_scope["status"] != "locked":
        return {**target, **locked_scope}

    try:
        import_result = run_osm_import(_import_args(target, args.apply))
        if args.apply and _saved_count(import_result) < MIN_SAVED_BEFORE_BBOX_FALLBACK:
            fallback = _run_expanded_bbox_fallback(target, args)
            import_result = {
                **import_result,
                "fallback_applied": True,
                "fallback_level": 1,
                "fallback_reason": "low_saved_places",
                "fallback_result": fallback,
            }

        address_backfill_result: dict[str, Any] | None = None
        if not args.skip_address_backfill:
            address_backfill_result = run_address_backfill(
                _address_backfill_args(
                    target["city"],
                    args.apply,
                    args.address_backfill_limit,
                    args.address_backfill_sleep,
                )
            )

        image_enrichment_result: dict[str, Any] | None = None
        if not args.skip_image_enrichment:
            image_enrichment_result = run_image_enrichment(
                _image_enrichment_args(target["city"], args.apply, args.image_enrichment_limit)
            )

        quality_cleanup_result: dict[str, Any] | None = None
        if not args.skip_quality_cleanup:
            quality_cleanup_result = run_quality_cleanup(_quality_cleanup_args(target["city"], args.apply))

        if args.apply:
            schedule_next(target)

        return {
            **target,
            "status": "success",
            "pipeline_order": [
                "osm_import",
                "address_backfill",
                "image_enrichment",
                "quality_cleanup",
            ],
            "import_result": import_result,
            "address_backfill_result": address_backfill_result,
            "image_enrichment_result": image_enrichment_result,
            "quality_cleanup_result": quality_cleanup_result,
        }

    except SystemExit as exc:
        return {**target, "status": "failed", "error": str(exc)}
    except Exception as exc:
        return {**target, "status": "failed", "error": str(exc)}

    finally:
        unlock_target(target)


def _import_args(target: dict[str, Any], apply: bool) -> list[str]:
    args = [
        "--city",
        target["city"],
        "--scope",
        target["scope"],
        "--profile",
        target["profile"],
        "--apply" if apply else "--dry-run",
    ]
    job_id = target.get("city_admin_import_job_id")
    if job_id is not None:
        args.extend(["--city-admin-import-job-id", str(job_id)])
    return args


def _address_backfill_args(city_slug: str, apply: bool, limit: int, sleep_seconds: float) -> list[str]:
    return [
        "--city",
        city_slug,
        "--limit",
        str(limit),
        "--sleep",
        str(sleep_seconds),
        "--apply" if apply else "--dry-run",
    ]


def _image_enrichment_args(city_slug: str, apply: bool, limit: int) -> list[str]:
    return [
        "--city",
        city_slug,
        "--limit",
        str(limit),
        "--apply" if apply else "--dry-run",
    ]


def _quality_cleanup_args(city_slug: str, apply: bool) -> list[str]:
    return ["--city", city_slug, "--apply" if apply else "--dry-run"]


def _saved_count(result: dict[str, Any]) -> int:
    return int(result.get("created") or 0) + int(result.get("updated") or 0) + int(result.get("unchanged") or 0)


def _run_expanded_bbox_fallback(target: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    with SessionLocal() as db:
        from models.city import City
        from models.city_import_scope import CityImportScope

        city = db.query(City).filter(City.slug == target["city"]).first()
        scope = (
            db.query(CityImportScope)
            .filter(CityImportScope.city_id == getattr(city, "id", None), CityImportScope.code == target["scope"])
            .first()
        )
        if scope is None or not isinstance(scope.bbox, dict):
            return {"status": "skipped", "reason": "scope_bbox_missing"}
        scope.bbox = _expanded_bbox(scope.bbox, BBOX_FALLBACK_EXPANSION_FACTOR)
        db.commit()
    result = run_osm_import(_import_args(target, args.apply))
    return {"status": "success", "expansion_factor": BBOX_FALLBACK_EXPANSION_FACTOR, "import_result": result}


def _expanded_bbox(bbox: dict[str, Any], factor: float) -> dict[str, float]:
    south = float(bbox["south"])
    west = float(bbox["west"])
    north = float(bbox["north"])
    east = float(bbox["east"])
    center_lat = (south + north) / 2
    center_lng = (west + east) / 2
    half_lat = max(0.001, (north - south) * factor / 2)
    half_lng = max(0.001, (east - west) * factor / 2)
    return {
        "south": center_lat - half_lat,
        "west": center_lng - half_lng,
        "north": center_lat + half_lat,
        "east": center_lng + half_lng,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
