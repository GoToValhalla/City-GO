from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.exc import IntegrityError

from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.city_import_scope import CityImportScope
from models.import_batch import ImportBatch
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation
from services.import_job_service import create_batch, finish_batch
from services.import_profiles import production_profile
from services.import_publication_gate import assess_import_quality
from services.import_state_service import update_import_state
from services.place_public_visibility import is_public_hidden_category
from services.place_field_provenance_service import record_place_field_provenance
from services.review_queue_service import ensure_review_item, safe_import_job_id
from services.place_import_lifecycle_service import (
    apply_accepted_import_to_place,
    existing_place_must_be_hidden,
    hide_place,
    mark_missing_place,
)
from services.osm_fetch_retry import DEFAULT_OSM_RETRY_CONFIG, fetch_osm_objects_with_retry
from services.osm_tile_planner import TilePlannerConfig, TilePlannerError, plan_tiles
from services.import_tile_run_service import (
    ensure_tile_runs,
    mark_tile_completed,
    mark_tile_failed,
    mark_tile_running,
    next_unfinished_tile_run,
    retry_failed_tile_runs,
    tile_progress_diagnostics,
)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

MAX_RAW_OBJECTS = 2500

# CITYGO-319: tile mode activates ONLY when the bbox exceeds these limits
# (i.e. plan_tiles() would produce more than one tile). Every current
# production scope bbox is well within 0.5deg in both dimensions (verified
# against data/config/import_targets.json — max observed span is ~0.45deg
# for almaty/tourist_core), so this default is a no-op for all existing
# imports: they keep planning to exactly one tile and take the exact same
# single-shot code path as before this task.
TILE_PLANNER_CONFIG = TilePlannerConfig()

DISPLAY_NAME_KEYS = (
    "name:ru",
    "name:en",
    "official_name:ru",
    "official_name:en",
    "official_name",
    "name",
    "brand",
    "operator",
)

BAD_NAME_VALUES = {
    "yes",
    "no",
    "none",
    "null",
    "unknown",
    "fixme",
    "todo",
    "n/a",
    "na",
}

PROFILE_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "tourist_core": [
        ("tourism", "attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium"),
        ("historic", None),
        ("amenity", "cafe|restaurant"),
        ("leisure", "park|garden|nature_reserve|playground"),
        ("natural", "beach|water|wood"),
    ],
    "food_and_coffee": [
        ("amenity", "cafe|restaurant|fast_food|bar|pub|food_court"),
        ("shop", "bakery|confectionery|coffee|tea|ice_cream"),
        ("cuisine", None),
    ],
    "nature_walk": [
        ("leisure", "park|garden|nature_reserve|playground"),
        ("natural", "beach|water|wood|peak"),
        ("tourism", "viewpoint|information"),
    ],
    "useful_services": [
        ("amenity", "toilets|pharmacy|atm|parking|shelter|bank|clinic|hospital|police"),
    ],
}

CATEGORY_NAMES: dict[str, str] = {
    "cafe": "Кафе",
    "food": "Еда",
    "walk": "Прогулка",
    "museum": "Музей",
    "culture": "Культура",
    "park": "Парк",
    "beach": "Пляж",
    "viewpoint": "Смотровая точка",
    "useful": "Полезное",
    "health": "Здоровье",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--city-admin-import-job-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)

    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    if not production_profile(args.profile):
        raise SystemExit(f"Profile is not production-safe: {args.profile}")

    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == args.city).first()
        if city is None:
            raise SystemExit(f"Unknown city: {args.city}")

        scope = db.query(CityImportScope).filter_by(city_id=city.id, code=args.scope).first()
        if scope is None:
            raise SystemExit(f"Unknown scope: {args.scope}")

        if not scope.enabled or scope.status == "paused":
            raise SystemExit(f"Scope is not importable: {args.scope}")

        bbox = _bbox(scope)

        # CITYGO-319: tile mode only ever activates for --apply, and only
        # when plan_tiles() genuinely produces more than one tile for this
        # bbox. A --dry-run request, or any bbox that fits in a single
        # tile (which is every current production scope — see
        # TILE_PLANNER_CONFIG's comment above), takes the exact same
        # single-shot fetch -> normalize -> apply path this function has
        # always taken. Any planning error (TilePlannerError) is treated
        # the same way — fall back to the single-shot path rather than
        # let a new, still-young component block an import that used to
        # work.
        if args.apply:
            tile_plan = None
            try:
                tile_plan = plan_tiles(
                    city_slug=city.slug,
                    scope_code=scope.code,
                    profile=args.profile,
                    bbox=bbox,
                    config=TILE_PLANNER_CONFIG,
                )
            except TilePlannerError:
                tile_plan = None
            if tile_plan is not None and tile_plan.tile_count > 1:
                return _apply_import_tiled(db, city, scope, args.profile, tile_plan, args.city_admin_import_job_id)

        raw_objects = _fetch_osm_objects(bbox, args.profile)

        if len(raw_objects) > MAX_RAW_OBJECTS:
            raise SystemExit(
                f"Too many OSM objects for {city.slug}/{scope.code}: "
                f"{len(raw_objects)} > {MAX_RAW_OBJECTS}. Narrow bbox or profile."
            )

        normalized = [_normalize_osm_object(item, city.slug) for item in raw_objects]

        if args.dry_run:
            return _dry_run_summary(city.slug, scope.code, args.profile, raw_objects, normalized)

        return _apply_import(db, city, scope, args.profile, raw_objects, normalized, args.city_admin_import_job_id)


def _dry_run_summary(
    city_slug: str,
    scope_code: str,
    profile: str,
    raw_objects: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
) -> dict[str, object]:
    accepted_items = [item for item in normalized if item["accepted"]]
    rejected_items = [item for item in normalized if not item["accepted"]]

    return {
        "mode": "dry_run",
        "city": city_slug,
        "scope": scope_code,
        "profile": profile,
        "raw_count": len(raw_objects),
        "normalized_count": len(accepted_items),
        "rejected_count": len(rejected_items),
        "accepted_categories": dict(Counter(item["category"] for item in accepted_items)),
        "rejection_reasons": dict(Counter(item["rejection_reason"] for item in rejected_items)),
        "production_changes": False,
    }


def _bbox(scope: CityImportScope) -> dict[str, float]:
    if not scope.bbox:
        raise SystemExit(f"Scope has no bbox: {scope.code}")

    bbox = scope.bbox

    try:
        return {
            "south": float(bbox["south"]),
            "west": float(bbox["west"]),
            "north": float(bbox["north"]),
            "east": float(bbox["east"]),
        }
    except KeyError as exc:
        raise SystemExit(f"Scope bbox must contain south/west/north/east: missing {exc}") from exc


def _fetch_osm_objects(bbox: dict[str, float], profile: str) -> list[dict[str, Any]]:
    filters = PROFILE_FILTERS.get(profile)
    if not filters:
        raise SystemExit(f"Unsupported OSM import profile: {profile}")

    clauses = []
    area = f'({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]})'

    for key, value_pattern in filters:
        if value_pattern:
            selector = f'["{key}"~"^({value_pattern})$"]'
        else:
            selector = f'["{key}"]'

        clauses.extend(
            [
                f"node{selector}{area};",
                f"way{selector}{area};",
                f"relation{selector}{area};",
            ]
        )

    query = f"""
    [out:json][timeout:45];
    (
      {' '.join(clauses)}
    );
    out center tags;
    """

    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "CityGoImporter/1.0"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return list(payload.get("elements", []))


def _normalize_osm_object(item: dict[str, Any], city_slug: str) -> dict[str, Any]:
    tags = item.get("tags") or {}

    source_external_id = f'osm:{item.get("type")}:{item.get("id")}'
    source_url = _osm_url(item)

    lat = item.get("lat") or (item.get("center") or {}).get("lat")
    lng = item.get("lon") or (item.get("center") or {}).get("lon")
    category = _category(tags)
    lifecycle_status = _source_lifecycle_status(tags)
    raw_name = _raw_osm_name(tags)
    name = _display_name(tags)

    if lifecycle_status in {"closed", "temporarily_closed", "removed_from_source"}:
        return _rejected(
            item=item,
            source_external_id=source_external_id,
            source_url=source_url,
            reason=f"source_{lifecycle_status}",
        )

    if lat is None or lng is None:
        return _rejected(item, source_external_id, source_url, "missing_coordinates")

    if category is None:
        return _rejected(item, source_external_id, source_url, "unsupported_category")

    if is_public_hidden_category(category):
        return _rejected(item, source_external_id, source_url, "hidden_category")

    if not name:
        if raw_name:
            return _rejected(item, source_external_id, source_url, "bad_name")
        name = _fallback_title(category, source_external_id)
    if not name:
        return _rejected(item, source_external_id, source_url, "missing_name")

    slug = _place_slug(city_slug, category, name, source_external_id)

    return {
        "accepted": True,
        "source_external_id": source_external_id,
        "source_url": source_url,
        "payload_hash": _hash(item),
        "raw_name": raw_name,
        "raw_category": category,
        "raw_lat": float(lat),
        "raw_lng": float(lng),
        "raw_payload": item,
        "lifecycle_status": lifecycle_status,
        "slug": slug,
        "title": name,
        "category": category,
        "address": _address(tags),
        "short_description": _description(name, category),
        "opening_hours": _opening_hours(tags),
        "website": tags.get("website") or tags.get("contact:website"),
        "phone": tags.get("phone") or tags.get("contact:phone"),
    }


def _raw_osm_name(tags: dict[str, Any]) -> str | None:
    for key in DISPLAY_NAME_KEYS:
        value = tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _display_name(tags: dict[str, Any]) -> str | None:
    for key in DISPLAY_NAME_KEYS:
        cleaned = _clean_display_name(tags.get(key))
        if cleaned:
            return cleaned

    return None


def _clean_display_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = cleaned.strip(" \t\r\n,.;:|/\\-–—_")

    if not cleaned:
        return None

    if _is_bad_display_name(cleaned):
        return None

    return cleaned


def _is_bad_display_name(value: str) -> bool:
    normalized = value.lower().strip()
    compact = re.sub(r"\s+", "", normalized)

    if compact in BAD_NAME_VALUES:
        return True

    numeric_candidate = re.sub(r"[№#\s,.;:|/\\\-–—_()+]+", "", normalized)
    if numeric_candidate.isdigit():
        return True

    if re.fullmatch(r"\d+[a-zа-яё]?", numeric_candidate, flags=re.IGNORECASE):
        return True

    return False


def _source_lifecycle_status(tags: dict[str, Any]) -> str:
    lifecycle_values = {
        "abandoned",
        "closed",
        "demolished",
        "destroyed",
        "disused",
        "removed",
        "razed",
    }

    if tags.get("temporary") == "yes":
        return "temporarily_closed"

    if tags.get("disused") == "yes":
        return "closed"

    if tags.get("abandoned") == "yes":
        return "closed"

    if tags.get("demolished") == "yes" or tags.get("destroyed") == "yes":
        return "removed_from_source"

    if tags.get("was:amenity") or tags.get("was:shop") or tags.get("was:tourism"):
        return "removed_from_source"

    for key in tags:
        prefix = key.split(":", 1)[0]
        if prefix in lifecycle_values:
            if prefix in {"demolished", "destroyed", "removed", "razed"}:
                return "removed_from_source"
            return "closed"

    opening_hours = str(tags.get("opening_hours") or "").lower().strip()
    if opening_hours in {"closed", "off"}:
        return "temporarily_closed"

    return "active"


def _rejected(
    item: dict[str, Any],
    source_external_id: str,
    source_url: str,
    reason: str,
) -> dict[str, Any]:
    tags = item.get("tags") or {}
    lat = item.get("lat") or (item.get("center") or {}).get("lat")
    lng = item.get("lon") or (item.get("center") or {}).get("lon")

    return {
        "accepted": False,
        "source_external_id": source_external_id,
        "source_url": source_url,
        "payload_hash": _hash(item),
        "raw_name": _raw_osm_name(tags),
        "raw_category": _category(tags),
        "raw_lat": float(lat) if lat is not None else None,
        "raw_lng": float(lng) if lng is not None else None,
        "raw_payload": item,
        "lifecycle_status": _source_lifecycle_status(tags),
        "rejection_reason": reason,
    }


def _category(tags: dict[str, Any]) -> str | None:
    amenity = tags.get("amenity")
    tourism = tags.get("tourism")
    leisure = tags.get("leisure")
    natural = tags.get("natural")
    historic = tags.get("historic")
    shop = tags.get("shop")

    if amenity == "cafe" or shop in {"coffee", "tea"}:
        return "cafe"

    if amenity in {"restaurant", "fast_food", "bar", "pub", "food_court"}:
        return "food"

    if shop in {"bakery", "confectionery", "ice_cream"}:
        return "food"

    if tourism == "museum":
        return "museum"

    if tourism in {"attraction", "gallery", "artwork"} or historic:
        return "culture"

    if tourism == "viewpoint":
        return "viewpoint"

    if leisure in {"park", "garden", "nature_reserve", "playground"}:
        return "park"

    if natural == "beach":
        return "beach"

    if natural in {"water", "wood", "peak"}:
        return "walk"

    if amenity in {"toilets", "atm", "parking", "shelter", "bank", "police"}:
        return "useful"

    if amenity in {"pharmacy", "clinic", "hospital"}:
        return "health"

    return None


CHUNK_SIZE = 50

# processing_outcome -> which running tallies it contributes to.
_OUTCOME_COUNTER_FIELDS: dict[str, tuple[str, ...]] = {
    "created": ("created",),
    "updated": ("updated",),
    "unchanged": ("unchanged",),
    "needs_review": ("needs_review",),
    "rejected": ("rejected",),
    "hidden_needs_review": ("hidden_needs_review", "needs_review"),
    "hidden_rejected": ("hidden_rejected", "rejected"),
    "duplicate": ("duplicate",),
}


def _apply_import(
    db,
    city: City,
    scope: CityImportScope,
    profile: str,
    raw_objects: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
    city_admin_import_job_id: int | None = None,
    *,
    batch_id: int | None = None,
) -> dict[str, object]:
    if batch_id is not None:
        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).one()
    else:
        batch = create_batch(db, scope, mode="apply")
        batch.source_type = "osm"
        batch.raw_count = len(raw_objects)
        db.commit()
    resolved_batch_id = batch.id

    counters = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "needs_review": 0,
        "rejected": 0,
        "hidden_needs_review": 0,
        "hidden_rejected": 0,
        "duplicate": 0,
        "matched_existing": 0,
    }
    rejection_reasons: Counter[str] = Counter()

    try:
        completed_since_commit = 0
        for item in normalized:
            idempotency_key = f"{batch.id}:{item['source_external_id']}"
            already_done = (
                db.query(SourceObservation)
                .filter(SourceObservation.idempotency_key == idempotency_key)
                .filter(SourceObservation.processing_outcome.isnot(None))
                .first()
            )
            if already_done is not None:
                for field in _OUTCOME_COUNTER_FIELDS.get(already_done.processing_outcome, ()):
                    counters[field] += 1
                if already_done.match_status == "matched_existing_place":
                    counters["matched_existing"] += 1
                if already_done.rejection_reason and already_done.processing_outcome in {"rejected", "hidden_rejected"}:
                    rejection_reasons[str(item.get("rejection_reason") or "unknown")] += 1
                continue

            _process_one_item(
                db,
                city=city,
                scope=scope,
                batch=batch,
                item=item,
                city_admin_import_job_id=city_admin_import_job_id,
                counters=counters,
                rejection_reasons=rejection_reasons,
            )

            completed_since_commit += 1
            if completed_since_commit >= CHUNK_SIZE:
                db.commit()
                db.expire_all()
                completed_since_commit = 0

        if completed_since_commit:
            db.commit()
            db.expire_all()

        deactivated_bad_places = _hide_bad_existing_places(db, city.id, scope.id)
        missing_stats = _mark_missing_sources(db, scope.id, batch.id, normalized, city_admin_import_job_id)

        published_total = counters["created"] + counters["updated"] + counters["unchanged"]
        normalized_total = published_total + counters["needs_review"] + counters["hidden_needs_review"]
        needs_review_total = counters["needs_review"] + counters["hidden_needs_review"] + counters["hidden_rejected"] + missing_stats["needs_review"]
        rejected_total = counters["rejected"] + counters["hidden_rejected"]
        hidden_total = counters["hidden_needs_review"] + counters["hidden_rejected"]
        # accepted == every normalized item where item["accepted"] was True at
        # _normalize_osm_object() time — i.e. everything that reached
        # _process_one_item's post-rejection branch. normalized_total already
        # sums every accepted outcome (created/updated/unchanged/needs_review/
        # hidden_needs_review), so accepted_total is exactly normalized_total:
        # nothing here is recomputed independently, only relabeled for the
        # funnel view.
        accepted_total = normalized_total

        # Funnel: a truthful accounting of every decision point already made
        # above, reorganized into the canonical stage names — no value here
        # is computed anywhere except where the decision was actually made.
        # "requested" has no distinct meaning from "fetched" in this pipeline
        # (the Overpass query IS the request; there is no separate
        # "requested vs returned" concept upstream), so it intentionally
        # equals raw_count rather than inventing a different number.
        # "deduplicated" has no implementation in this pipeline at all (no
        # raw-object dedup step exists before normalization) — it is
        # reported as unavailable, never as 0, so an operator never mistakes
        # "no dedup logic runs" for "we checked and found zero duplicates".
        funnel = {
            "requested": batch.raw_count,
            "fetched": batch.raw_count,
            "deduplicated": "unavailable",
            "normalized": len(normalized),
            "accepted": accepted_total,
            "rejected_by_reason": dict(rejection_reasons),
            "matched_existing": counters["matched_existing"],
            "created": counters["created"],
            "updated": counters["updated"],
            "unchanged": counters["unchanged"],
            "hidden": hidden_total,
            "sent_to_review": needs_review_total,
            "failed": 0,
        }

        batch.normalized_count = normalized_total
        batch.published_count = published_total
        batch.needs_review_count = needs_review_total
        batch.rejected_count = rejected_total
        batch.duplicate_count = counters["duplicate"]
        batch.errors_count = 0
        batch.diff_summary = {
            "profile": profile,
            "created": counters["created"],
            "updated": counters["updated"],
            "unchanged": counters["unchanged"],
            "needs_review": needs_review_total,
            "rejected": rejected_total,
            "hidden": hidden_total,
            "duplicate": counters["duplicate"],
            "rejection_reasons": dict(rejection_reasons),
            "deactivated_bad_places": deactivated_bad_places,
            "missing_from_source": missing_stats["missing_from_source"],
            "hidden_missing_places": missing_stats["hidden_missing_places"],
            "note": "Scoped OSM import applied with lifecycle update rules",
            "funnel": funnel,
        }

        finish_batch(db, batch, "success")
        state = update_import_state(db, batch, "success")
        state.import_profile = profile
        state.last_missing_from_source_count = missing_stats["missing_from_source"]
        _update_scope_after_success(db, scope)

        return {
            "mode": "apply",
            "city": city.slug,
            "scope": scope.code,
            "profile": profile,
            "batch_id": batch.id,
            "raw_count": batch.raw_count,
            "created": counters["created"],
            "updated": counters["updated"],
            "unchanged": counters["unchanged"],
            "needs_review": needs_review_total,
            "rejected": rejected_total,
            "rejection_reasons": dict(rejection_reasons),
            "hidden": hidden_total,
            "deactivated_bad_places": deactivated_bad_places,
            "missing_from_source": missing_stats["missing_from_source"],
            "hidden_missing_places": missing_stats["hidden_missing_places"],
            "status": "success",
            "funnel": funnel,
        }

    except Exception as exc:
        db.rollback()
        batch = db.query(ImportBatch).filter(ImportBatch.id == resolved_batch_id).first()
        if batch:
            finish_batch(db, batch, "failed", error_count=1)
            update_import_state(db, batch, "failed", str(exc))
        raise


_TILE_RESULT_COUNTER_FIELDS = (
    "created", "updated", "unchanged", "needs_review", "rejected", "hidden",
    "missing_from_source", "hidden_missing_places", "deactivated_bad_places",
)


def _apply_import_tiled(
    db,
    city: City,
    scope: CityImportScope,
    profile: str,
    tile_plan,
    city_admin_import_job_id: int | None,
) -> dict[str, object]:
    """CITYGO-319: tiled OSM apply. Each tile is fetched (with retry via
    services/osm_fetch_retry.py) and applied (services/import_city_osm.py's
    existing _apply_import, unmodified — one ImportBatch per tile) fully
    independently, in the tile plan's deterministic sequence order.

    Resume (CITYGO-320) + execution identity (CITYGO-338):
    services/import_tile_run_service.py persists one ImportTileRun row per
    (execution_id, tile_id) before any fetch happens. execution_id is
    derived from city_admin_import_job_id when a job exists — retrying the
    SAME job (same job.id, see services/admin_city_import_job_service.py's
    retry path) resumes via the same execution_id, finding exactly where a
    crashed or interrupted run left off, never re-fetching or re-applying
    an already-completed tile. When there is no job (a bare CLI --apply
    run), a fresh execution_id is minted for this call — that run's
    checkpoints can never be resumed by identity and can never collide
    with a concurrent run's checkpoints. A brand-new import execution
    (a new job, or a new no-job CLI invocation) always gets its own
    execution_id and therefore its own fresh rows, processing every tile
    even if an older execution already completed the same coordinates —
    older executions' rows are never deleted, they remain as history.
    Already-completed tiles' real Place/SourceObservation rows are never
    touched again — nothing is lost on a retry of the same execution.

    Failed tiles get one explicit retry pass per call
    (retry_failed_tile_runs, bounded by MAX_TILE_RETRY_ATTEMPTS) before
    resuming — a tile that has failed repeatedly stays terminal rather
    than being retried forever.

    No new places are duplicated: each tile's own ImportBatch reuses the
    exact same SourceObservation idempotency scoping and
    apply_accepted_import_to_place() matching logic that a single-shot
    import already used — this function does not change any matching,
    publication, or review code, it only calls the existing _apply_import
    once per tile instead of once per scope.
    """
    run_started_at = datetime.utcnow()
    execution_id = f"job:{city_admin_import_job_id}" if city_admin_import_job_id is not None else f"adhoc:{uuid.uuid4()}"
    tile_runs = ensure_tile_runs(
        db,
        execution_id=execution_id,
        scope_id=scope.id,
        city_admin_import_job_id=city_admin_import_job_id,
        planner_version=tile_plan.planner_version,
        tiles=tile_plan.tiles,
    )
    retry_failed_tile_runs(db, tile_runs)
    db.commit()

    aggregate = {field: 0 for field in _TILE_RESULT_COUNTER_FIELDS}
    tile_diagnostics: list[dict[str, object]] = []
    retried_tile_count = 0
    total_retry_attempts = 0

    tile_by_id = {tile.tile_id: tile for tile in tile_plan.tiles}

    while True:
        tile_run = next_unfinished_tile_run(tile_runs)
        if tile_run is None:
            break
        tile = tile_by_id[tile_run.tile_id]
        tile_bbox = {"south": tile.south, "west": tile.west, "north": tile.north, "east": tile.east}

        mark_tile_running(db, tile_run)
        db.commit()

        fetch_outcome = fetch_osm_objects_with_retry(
            lambda: _fetch_osm_objects(tile_bbox, profile),
            config=DEFAULT_OSM_RETRY_CONFIG,
        )
        if fetch_outcome.attempt_count > 1:
            retried_tile_count += 1
        total_retry_attempts += max(fetch_outcome.attempt_count - 1, 0)

        if not fetch_outcome.success:
            mark_tile_failed(
                db,
                tile_run,
                failure_reason=fetch_outcome.final_error or "OSM fetch failed",
                retry_attempts=max(fetch_outcome.attempt_count - 1, 0),
            )
            db.commit()
            tile_diagnostics.append(
                {
                    "tile_id": tile.tile_id,
                    "sequence": tile.sequence,
                    "status": "failed",
                    "failure_reason": fetch_outcome.final_error,
                    "retry_attempts": max(fetch_outcome.attempt_count - 1, 0),
                }
            )
            continue

        raw_objects = fetch_outcome.value or []
        if len(raw_objects) > MAX_RAW_OBJECTS:
            reason = f"Too many OSM objects in tile {tile.tile_id}: {len(raw_objects)} > {MAX_RAW_OBJECTS}"
            mark_tile_failed(db, tile_run, failure_reason=reason, retry_attempts=max(fetch_outcome.attempt_count - 1, 0))
            db.commit()
            tile_diagnostics.append(
                {"tile_id": tile.tile_id, "sequence": tile.sequence, "status": "failed", "failure_reason": reason, "retry_attempts": max(fetch_outcome.attempt_count - 1, 0)}
            )
            continue

        normalized = [_normalize_osm_object(item, city.slug) for item in raw_objects]

        try:
            tile_result = _apply_import(db, city, scope, profile, raw_objects, normalized, city_admin_import_job_id)
        except Exception as exc:  # noqa: BLE001 — a single tile's apply failure must not lose other tiles' progress
            mark_tile_failed(db, tile_run, failure_reason=str(exc)[:2000], retry_attempts=max(fetch_outcome.attempt_count - 1, 0))
            db.commit()
            tile_diagnostics.append(
                {"tile_id": tile.tile_id, "sequence": tile.sequence, "status": "failed", "failure_reason": str(exc)[:500], "retry_attempts": max(fetch_outcome.attempt_count - 1, 0)}
            )
            continue

        for field in _TILE_RESULT_COUNTER_FIELDS:
            aggregate[field] += int(tile_result.get(field) or 0)

        mark_tile_completed(
            db,
            tile_run,
            batch_id=tile_result.get("batch_id"),
            counters={field: tile_result.get(field) for field in _TILE_RESULT_COUNTER_FIELDS},
            retry_attempts=max(fetch_outcome.attempt_count - 1, 0),
        )
        db.commit()
        tile_diagnostics.append(
            {
                "tile_id": tile.tile_id,
                "sequence": tile.sequence,
                "status": "completed",
                "batch_id": tile_result.get("batch_id"),
                "retry_attempts": max(fetch_outcome.attempt_count - 1, 0),
            }
        )

    progress = tile_progress_diagnostics(tile_runs, started_at=run_started_at)
    elapsed_seconds = (datetime.utcnow() - run_started_at).total_seconds()

    return {
        "mode": "apply",
        "city": city.slug,
        "scope": scope.code,
        "profile": profile,
        "status": "success" if progress["failed"] == 0 else "partial_success",
        "tiled": True,
        "planner_version": tile_plan.planner_version,
        "raw_count": None,
        **aggregate,
        "tile_diagnostics": {
            "execution_id": execution_id,
            "total_tiles": progress["total_tiles"],
            "completed": progress["completed"],
            "failed": progress["failed"],
            "retried_tiles": retried_tile_count,
            "total_retry_attempts": total_retry_attempts,
            "elapsed_seconds": elapsed_seconds,
            "tiles": tile_diagnostics,
        },
    }


def _process_one_item(
    db,
    *,
    city: City,
    scope: CityImportScope,
    batch: ImportBatch,
    item: dict[str, Any],
    city_admin_import_job_id: int | None,
    counters: dict[str, int],
    rejection_reasons: Counter[str],
) -> None:
    observation = _save_source_observation(db, city, scope, batch, item)

    if not item["accepted"]:
        rejection_reasons[str(item.get("rejection_reason") or "unknown")] += 1
        hidden_place = _find_existing_place(db, city.id, item)
        before_public = _public_state_snapshot(hidden_place) if hidden_place is not None else None
        decision = _hide_existing_rejected_place(db, city.id, item)
        if decision is not None:
            _enqueue_place_change_review(
                db,
                city=city,
                batch=batch,
                city_admin_import_job_id=city_admin_import_job_id,
                place=hidden_place,
                decision=decision,
                item=item,
                before_public=before_public,
            )
            observation.processing_outcome = "hidden_rejected"
            counters["hidden_rejected"] += 1
        else:
            observation.processing_outcome = "rejected"
            counters["rejected"] += 1
        return

    category = _get_or_create_category(db, item["category"])
    place = _find_existing_place(db, city.id, item)
    matched_existing = place is not None
    if matched_existing:
        counters["matched_existing"] += 1
    before_public = _public_state_snapshot(place) if matched_existing else None
    item_outcome = None

    if place is None:
        _gate = assess_import_quality(
            title=item["title"],
            lat=item["raw_lat"],
            lng=item["raw_lng"],
            category=item["category"],
            confidence=0.7,
            source="osm",
            address=item.get("address"),
        )
        place = Place(
            city_id=city.id,
            category_id=category.id,
            slug=item["slug"],
            title=item["title"],
            short_description=item["short_description"],
            category=item["category"],
            address=item["address"],
            lat=item["raw_lat"],
            lng=item["raw_lng"],
            source="osm",
            source_url=item["source_url"],
            confidence=0.7,
            status="active",
            is_active=True,
            # Imported places stay private until an admin publishes the city.
            is_published=False,
            is_visible_in_catalog=False,
            is_route_eligible=False,
            is_searchable=False,
            publication_status="needs_review" if _gate.decision != "hidden" else _gate.publication_status,
            price_level=_price_level(item["category"]),
            average_visit_duration_minutes=_visit_duration(item["category"]),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(place)
        db.flush()
        item_outcome = "created"

    decision = apply_accepted_import_to_place(
        place=place,
        item=item,
        category_id=category.id,
        visit_duration_minutes=_visit_duration(item["category"]),
    )

    if matched_existing:
        if decision.action == "needs_review":
            _enqueue_place_change_review(
                db,
                city=city,
                batch=batch,
                city_admin_import_job_id=city_admin_import_job_id,
                place=place,
                decision=decision,
                item=item,
                before_public=before_public,
            )
            item_outcome = "needs_review"
        elif decision.action == "unchanged":
            item_outcome = "unchanged"
        elif decision.action == "hidden":
            _enqueue_place_change_review(
                db,
                city=city,
                batch=batch,
                city_admin_import_job_id=city_admin_import_job_id,
                place=place,
                decision=decision,
                item=item,
                before_public=before_public,
            )
            item_outcome = "hidden_needs_review"
        else:
            item_outcome = "updated"

    observation.canonical_place_id = place.id
    observation.match_status = "matched_existing_place" if matched_existing else "new_source_object"
    observation.normalization_status = "linked_to_place"

    if decision.review_reasons:
        observation.rejection_reason = ",".join(decision.review_reasons)

    _ensure_scope_link(db, place.id, scope.id, batch.id)
    _ensure_source_presence(db, place.id, item["source_external_id"], observation.id, batch.id)
    record_place_field_provenance(
        db,
        place=place,
        source="osm",
        source_url=item["source_url"],
        values={
            "title": item["title"],
            "category": item["category"],
            "address": item.get("address"),
            "opening_hours": item.get("opening_hours"),
            "website": item.get("website"),
            "phone": item.get("phone"),
            "lat": item["raw_lat"],
            "lng": item["raw_lng"],
        },
    )

    observation.processing_outcome = item_outcome
    counters[item_outcome] += 1



def _public_state_snapshot(place: Place | None) -> dict[str, object] | None:
    if place is None:
        return None
    return {
        "was_public": bool(place.is_published and place.is_visible_in_catalog and place.is_searchable),
        "status": place.status,
        "is_active": bool(place.is_active),
        "is_published": bool(place.is_published),
        "is_visible_in_catalog": bool(place.is_visible_in_catalog),
        "is_route_eligible": bool(place.is_route_eligible),
        "is_searchable": bool(place.is_searchable),
        "publication_status": place.publication_status,
    }


def _enqueue_place_change_review(
    db,
    *,
    city: City,
    batch: ImportBatch,
    city_admin_import_job_id: int | None,
    place: Place | None,
    decision,
    item: dict[str, Any],
    before_public: dict[str, object] | None,
) -> None:
    if place is None or decision.action == "unchanged":
        return

    changes = {
        field_name: {
            "before": _json_value(change.get("before")),
            "after": _json_value(change.get("after")),
        }
        for field_name, change in (decision.change_set or {}).items()
        if field_name not in {"updated_at", "last_verified_at", "unpublished_at"}
    }
    if not changes:
        changes = {
            "status": {
                "before": (before_public or {}).get("status"),
                "after": place.status,
            }
        }

    reason = str((decision.review_reasons or ["source_data_changed"])[0])
    severity = "high" if reason in {"large_coordinate_drift", "source_removed", "source_closed"} else "medium"
    linked_job_id, job_link_issue = safe_import_job_id(db, city_admin_import_job_id)
    payload: dict[str, object] = {
        "kind": "place_change",
        "source": "osm",
        "import_batch_id": batch.id,
        "city_admin_import_job_id": linked_job_id,
        "source_url": item.get("source_url"),
        "decision": decision.action,
        "place_title": place.title,
        "before_public": before_public or {},
        "changes": changes,
        "review_reasons": list(decision.review_reasons or []),
    }
    if job_link_issue is not None:
        payload["job_link_issue"] = job_link_issue
    ensure_review_item(
        db,
        city_id=city.id,
        place_id=place.id,
        job_id=linked_job_id,
        field_name="place_change",
        reason=reason,
        severity=severity,
        payload=payload,
    )


def _json_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def _find_existing_place(db, city_id: int, item: dict[str, Any]) -> Place | None:
    by_source_url = (
        db.query(Place)
        .filter(
            Place.city_id == city_id,
            Place.source_url == item["source_url"],
        )
        .first()
    )

    if by_source_url:
        return by_source_url

    by_slug = (
        db.query(Place)
        .filter(
            Place.city_id == city_id,
            Place.slug == item.get("slug", ""),
        )
        .first()
    )

    return by_slug


def _hide_existing_rejected_place(db, city_id: int, item: dict[str, Any]):
    place = (
        db.query(Place)
        .filter(
            Place.city_id == city_id,
            Place.source_url == item["source_url"],
        )
        .first()
    )

    if not place:
        return None

    reason = str(item.get("rejection_reason") or "rejected_import_object")
    status = _status_for_rejection(reason)

    return hide_place(
        place=place,
        reason=reason,
        status=status,
    )


def _status_for_rejection(reason: str) -> str:
    if reason == "source_temporarily_closed":
        return "temporarily_closed"

    if reason == "source_closed":
        return "closed"

    if reason == "source_removed_from_source":
        return "removed_from_source"

    return "draft"


def _hide_bad_existing_places(db, city_id: int, scope_id: int) -> int:
    places = (
        db.query(Place)
        .join(PlaceScopeLink, PlaceScopeLink.place_id == Place.id)
        .filter(
            Place.city_id == city_id,
            PlaceScopeLink.scope_id == scope_id,
            Place.is_active.is_(True),
        )
        .all()
    )

    hidden_count = 0

    for place in places:
        if existing_place_must_be_hidden(place):
            hide_place(
                place=place,
                reason="bad_existing_place",
                status="draft",
            )
            hidden_count += 1

    return hidden_count


def _save_source_observation(
    db,
    city: City,
    scope: CityImportScope,
    batch: ImportBatch,
    item: dict[str, Any],
) -> SourceObservation:
    idempotency_key = f"{batch.id}:{item['source_external_id']}"

    existing = (
        db.query(SourceObservation)
        .filter(SourceObservation.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        existing.source_url = item.get("source_url")
        existing.raw_name = item.get("raw_name")
        existing.raw_category = item.get("raw_category")
        existing.raw_lat = item.get("raw_lat")
        existing.raw_lng = item.get("raw_lng")
        existing.raw_payload = item.get("raw_payload") or {}
        existing.payload_hash = item["payload_hash"]
        existing.last_seen_at = datetime.utcnow()
        existing.seen_in_batch_id = batch.id
        existing.match_status = "new_source_object" if item["accepted"] else "rejected"
        existing.normalization_status = "normalized" if item["accepted"] else "rejected"
        existing.rejection_reason = item.get("rejection_reason")
        existing.confidence = 0.7 if item["accepted"] else 0.0
        db.flush()
        return existing

    observation = SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        scope_id=scope.id,
        source_type="osm",
        source_external_id=item["source_external_id"],
        source_object_type="osm",
        source_url=item.get("source_url"),
        raw_name=item.get("raw_name"),
        raw_category=item.get("raw_category"),
        raw_lat=item.get("raw_lat"),
        raw_lng=item.get("raw_lng"),
        raw_payload=item.get("raw_payload") or {},
        payload_hash=item["payload_hash"],
        idempotency_key=idempotency_key,
        seen_in_batch_id=batch.id,
        match_status="new_source_object" if item["accepted"] else "rejected",
        normalization_status="normalized" if item["accepted"] else "rejected",
        rejection_reason=item.get("rejection_reason"),
        confidence=0.7 if item["accepted"] else 0.0,
    )
    try:
        with db.begin_nested():
            db.add(observation)
            db.flush()
    except IntegrityError:
        # The nested SAVEPOINT above is rolled back automatically on
        # exception exit; only the failed insert is undone, not the batch's
        # outer transaction. A concurrent writer won the race for this key.
        existing = (
            db.query(SourceObservation)
            .filter(SourceObservation.idempotency_key == idempotency_key)
            .first()
        )
        if existing is None:
            raise
        return existing
    return observation


def _get_or_create_category(db, code: str) -> Category:
    category = db.query(Category).filter(Category.code == code).first()
    if category:
        return category

    category = Category(
        code=code,
        name=CATEGORY_NAMES.get(code, code),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(category)
    db.flush()
    return category


def _ensure_scope_link(db, place_id: int, scope_id: int, batch_id: int) -> None:
    existing = db.query(PlaceScopeLink).filter_by(place_id=place_id, scope_id=scope_id).first()
    if existing:
        existing.last_seen_batch_id = batch_id
        existing.updated_at = datetime.utcnow()
        return

    db.add(
        PlaceScopeLink(
            place_id=place_id,
            scope_id=scope_id,
            relation_type="imported_from_scope",
            first_seen_batch_id=batch_id,
            last_seen_batch_id=batch_id,
        )
    )


def _ensure_source_presence(
    db,
    place_id: int,
    source_external_id: str,
    source_observation_id: int,
    batch_id: int,
) -> None:
    existing = (
        db.query(PlaceSourcePresence)
        .filter_by(
            source_type="osm",
            source_external_id=source_external_id,
        )
        .first()
    )

    if existing:
        existing.place_id = place_id
        existing.source_observation_id = source_observation_id
        existing.last_seen_at = datetime.utcnow()
        existing.last_seen_batch_id = batch_id
        existing.consecutive_missing_count = 0
        existing.presence_status = "active_in_source"
        existing.updated_at = datetime.utcnow()
        return

    db.add(
        PlaceSourcePresence(
            place_id=place_id,
            source_observation_id=source_observation_id,
            source_type="osm",
            source_external_id=source_external_id,
            last_seen_batch_id=batch_id,
            presence_status="active_in_source",
        )
    )


def _mark_missing_sources(
    db,
    scope_id: int,
    batch_id: int,
    normalized: list[dict[str, Any]],
    city_admin_import_job_id: int | None,
) -> dict[str, int]:
    # Важно: seen должен учитывать все пришедшие из OSM объекты,
    # даже если они были отклонены нормализацией.
    # Иначе bad_name / unsupported_category / source_closed ошибочно считались бы missing_from_source.
    seen = {
        item["source_external_id"]
        for item in normalized
    }

    rows = (
        db.query(PlaceSourcePresence)
        .join(PlaceScopeLink, PlaceScopeLink.place_id == PlaceSourcePresence.place_id)
        .filter(PlaceScopeLink.scope_id == scope_id, PlaceSourcePresence.source_type == "osm")
        .all()
    )

    missing_rows = [row for row in rows if row.source_external_id not in seen]
    hidden_missing_places = 0

    for row in missing_rows:
        row.consecutive_missing_count += 1
        row.last_missing_at = datetime.utcnow()
        row.presence_status = _presence_status(row.consecutive_missing_count)
        row.last_seen_batch_id = row.last_seen_batch_id or batch_id
        row.updated_at = datetime.utcnow()

        if row.place_id is None:
            continue

        place = db.query(Place).filter(Place.id == row.place_id).first()
        if place is None:
            continue

        before_public = _public_state_snapshot(place)
        decision = mark_missing_place(
            place=place,
            missing_count=row.consecutive_missing_count,
        )
        if decision.action == "hidden":
            hidden_missing_places += 1
            city = db.query(City).filter(City.id == place.city_id).first()
            if city is not None:
                _enqueue_place_change_review(
                    db,
                    city=city,
                    batch=db.query(ImportBatch).filter(ImportBatch.id == batch_id).one(),
                    city_admin_import_job_id=city_admin_import_job_id,
                    place=place,
                    decision=decision,
                    item={"source_url": None},
                    before_public=before_public,
                )

    return {
        "missing_from_source": len(missing_rows),
        "hidden_missing_places": hidden_missing_places,
        "needs_review": hidden_missing_places,
    }


def _presence_status(missing_count: int) -> str:
    if missing_count == 1:
        return "missing_once"

    if missing_count == 2:
        return "missing_repeatedly"

    return "possible_removed"


def _update_scope_after_success(db, scope: CityImportScope) -> None:
    now = datetime.utcnow()
    scope.last_imported_at = now
    scope.updated_at = now
    db.commit()


def _address(tags: dict[str, Any]) -> str | None:
    """
    Строит адрес из OSM-тегов.
    Порядок: structured (street+house+city) > addr:place > addr:full / contact:address.
    Не придумывает адрес при отсутствии данных.
    """
    full = tags.get("addr:full") or tags.get("contact:address")
    street = tags.get("addr:street") or tags.get("contact:street")
    house = tags.get("addr:housenumber") or tags.get("contact:housenumber")
    city = (
        tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:village")
        or tags.get("contact:city")
    )
    place = tags.get("addr:place")

    if street:
        parts = [p for p in [street, house] if p]
        structured = ", ".join(parts)
        return f"{structured}, {city}" if city else structured

    if place:
        return f"{place}, {city}" if city else place

    return full or None


def _opening_hours(tags: dict[str, Any]) -> dict[str, object] | None:
    value = tags.get("opening_hours")
    if not value:
        return None

    return {
        "raw": value,
        "source": "osm",
    }


def _description(name: str, category: str) -> str:
    label = CATEGORY_NAMES.get(category, category)
    return f"{label}: {name}"


def _fallback_title(category: str, source_external_id: str) -> str | None:
    labels = {
        "park": "Парк",
        "viewpoint": "Смотровая точка",
        "culture": "Культурное место",
        "museum": "Музей",
        "walk": "Место для прогулки",
        "beach": "Пляж",
    }
    label = labels.get(category)
    if not label:
        return None
    suffix = source_external_id.rsplit(":", 1)[-1]
    return f"{label} OSM {suffix}"


def _price_level(category: str) -> int:
    return {
        "park": 0,
        "beach": 0,
        "walk": 0,
        "viewpoint": 0,
        "culture": 1,
        "museum": 1,
        "useful": 1,
        "health": 1,
        "cafe": 2,
        "food": 2,
    }.get(category, 1)


def _visit_duration(category: str) -> int:
    return {
        "cafe": 30,
        "food": 60,
        "museum": 75,
        "culture": 45,
        "viewpoint": 20,
        "park": 45,
        "beach": 60,
        "walk": 45,
        "useful": 10,
        "health": 10,
    }.get(category, 30)


def _osm_url(item: dict[str, Any]) -> str:
    osm_type = item.get("type")
    osm_id = item.get("id")
    return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"


def _hash(item: dict[str, Any]) -> str:
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _place_slug(city_slug: str, category: str, name: str, source_external_id: str) -> str:
    base = _slugify(name)
    source_suffix = source_external_id.replace("osm:", "").replace(":", "-")

    if not base:
        base = source_suffix

    return f"{city_slug}-{category}-{base}-{source_suffix}"[:250]


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-zа-яё0-9]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
