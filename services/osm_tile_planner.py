"""CITYGO-317: deterministic spatial tile planner for OSM ingestion.

Dark-launched, standalone module. Splits a city/scope bounding box into a
grid of stable rectangular tiles for a FUTURE tiled import strategy (see
services/destination_foundation_todo.py::DestinationImportStrategy.TILED
and models/city_import_scope.py's "Data Foundation V2" TODOs — this module
is the first concrete, testable implementation of a piece of that future
strategy, not another dead scaffold).

This module is NOT called by any current import code path. No existing
import job starts using tiles by importing this file — plan_tiles() must
be invoked explicitly, and nothing in data/scripts/import_city_osm.py,
services/admin_city_import_runner.py, or data/scripts/run_due_import_jobs.py
references it.

Determinism contract:
- The same (city_slug, scope_code, profile, bbox, config) always produces
  the same tile count, the same tile_ids, the same boundaries, and the
  same processing order (tiles are always sequenced south-to-north, then
  west-to-east within each row — sequence 1..N).
- Tile IDs are derived deterministically from city_slug, scope_code,
  profile, and each tile's normalized (fixed-precision) bounds. No random
  UUIDs are used anywhere in this module.
- The grid exactly partitions the bbox: each row/column is bbox_span /
  row_count (or / col_count), computed once and reused for every tile
  boundary, so adjacent tiles share an EXACT floating-point boundary value
  (no gaps, no overlap) — see "Boundary rules" below.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

PLANNER_VERSION = "osm_tile_planner_v1"

# Coordinates are rounded to this many decimal places before hashing/
# comparing, so floating point noise (e.g. 44.49910000000001 vs 44.4991)
# never changes a tile_id or a determinism check. ~1.1 cm precision at the
# equator — far finer than any real bbox/tile boundary in this system.
COORDINATE_PRECISION = 9

DEFAULT_MAX_TILE_WIDTH_DEG = 0.5
DEFAULT_MAX_TILE_HEIGHT_DEG = 0.5
DEFAULT_MAX_TILE_COUNT = 256


class TilePlannerError(ValueError):
    """Raised for any invalid/unsafe input — fail closed, never a partial plan."""


@dataclass(frozen=True)
class TilePlannerConfig:
    """Configurable limits. All fields have safe, explicit defaults —
    nothing here is inferred or guessed at call time."""

    max_tile_width_deg: float = DEFAULT_MAX_TILE_WIDTH_DEG
    max_tile_height_deg: float = DEFAULT_MAX_TILE_HEIGHT_DEG
    max_tile_count: int = DEFAULT_MAX_TILE_COUNT

    def __post_init__(self) -> None:
        if self.max_tile_width_deg <= 0:
            raise TilePlannerError(f"max_tile_width_deg must be positive, got {self.max_tile_width_deg!r}")
        if self.max_tile_height_deg <= 0:
            raise TilePlannerError(f"max_tile_height_deg must be positive, got {self.max_tile_height_deg!r}")
        if self.max_tile_count <= 0:
            raise TilePlannerError(f"max_tile_count must be positive, got {self.max_tile_count!r}")


@dataclass(frozen=True)
class Tile:
    tile_id: str
    city_slug: str
    scope_code: str
    profile: str
    south: float
    west: float
    north: float
    east: float
    sequence: int
    total_tiles: int


@dataclass(frozen=True)
class TilePlan:
    city_slug: str
    scope_code: str
    profile: str
    original_bbox: dict[str, float]
    tiles: tuple[Tile, ...]
    planner_version: str
    rows: int
    cols: int

    @property
    def tile_count(self) -> int:
        return len(self.tiles)

    def diagnostics(self) -> dict[str, Any]:
        """Truthful planning diagnostics (requirement 9) — every value here
        is read directly from already-computed plan state, nothing is
        estimated or fabricated."""
        first = self.tiles[0] if self.tiles else None
        return {
            "planner_version": self.planner_version,
            "city_slug": self.city_slug,
            "scope_code": self.scope_code,
            "profile": self.profile,
            "original_bbox": dict(self.original_bbox),
            "tile_count": self.tile_count,
            "rows": self.rows,
            "cols": self.cols,
            "tile_width_deg": round(first.east - first.west, COORDINATE_PRECISION) if first else None,
            "tile_height_deg": round(first.north - first.south, COORDINATE_PRECISION) if first else None,
            "rejection_reason": None,
        }


def plan_tiles_diagnostics(
    *,
    city_slug: str,
    scope_code: str,
    profile: str,
    bbox: dict[str, Any],
    config: TilePlannerConfig | None = None,
) -> dict[str, Any]:
    """Non-raising wrapper around plan_tiles() for callers that want a
    truthful diagnostics dict either way (requirement 9: original bbox,
    tile count, tile dimensions, planner version, rejection/error reason).
    Never fabricates a fallback plan on failure — a rejected bbox reports
    tile_count=0 and the exact rejection_reason, nothing else."""
    try:
        plan = plan_tiles(city_slug=city_slug, scope_code=scope_code, profile=profile, bbox=bbox, config=config)
    except TilePlannerError as exc:
        return {
            "planner_version": PLANNER_VERSION,
            "city_slug": city_slug,
            "scope_code": scope_code,
            "profile": profile,
            "original_bbox": dict(bbox),
            "tile_count": 0,
            "rows": None,
            "cols": None,
            "tile_width_deg": None,
            "tile_height_deg": None,
            "rejection_reason": str(exc),
        }
    return plan.diagnostics()


def _round(value: float) -> float:
    return round(float(value), COORDINATE_PRECISION)


def _validate_bbox(bbox: dict[str, Any]) -> tuple[float, float, float, float]:
    missing = [key for key in ("south", "west", "north", "east") if key not in bbox]
    if missing:
        raise TilePlannerError(f"bbox missing required keys: {', '.join(sorted(missing))}")

    try:
        south = float(bbox["south"])
        west = float(bbox["west"])
        north = float(bbox["north"])
        east = float(bbox["east"])
    except (TypeError, ValueError) as exc:
        raise TilePlannerError(f"bbox values must be numeric: {exc}") from exc

    for name, value in (("south", south), ("north", north)):
        if not (-90.0 <= value <= 90.0):
            raise TilePlannerError(f"{name}={value} out of valid latitude range [-90, 90]")
    for name, value in (("west", west), ("east", east)):
        if not (-180.0 <= value <= 180.0):
            raise TilePlannerError(f"{name}={value} out of valid longitude range [-180, 180]")

    if south >= north:
        raise TilePlannerError(f"south ({south}) must be strictly less than north ({north})")

    # Antimeridian crossing (e.g. west=170, east=-170) is explicitly NOT
    # supported by this planner — requirement 6 says it must fail
    # explicitly unless already correctly supported, and no antimeridian-
    # aware wrapping logic exists anywhere in this codebase's OSM import
    # path today, so failing closed here is the only correct option.
    if west >= east:
        raise TilePlannerError(
            f"west ({west}) must be strictly less than east ({east}); "
            "antimeridian-crossing bboxes (west >= east) are not supported by this planner"
        )

    return _round(south), _round(west), _round(north), _round(east)


def _tile_id(city_slug: str, scope_code: str, profile: str, south: float, west: float, north: float, east: float) -> str:
    """Deterministic, non-random tile identifier. Same inputs -> same id,
    always, on any machine, in any process — derived only from the
    identifying fields listed in requirement 4 (city, scope/profile,
    normalized bounds), hashed for a short, stable, filesystem/URL-safe
    token rather than concatenating raw floats into an unwieldy string."""
    normalized = f"{city_slug}|{scope_code}|{profile}|{south:.9f}|{west:.9f}|{north:.9f}|{east:.9f}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"tile_{digest}"


def plan_tiles(
    *,
    city_slug: str,
    scope_code: str,
    profile: str,
    bbox: dict[str, Any],
    config: TilePlannerConfig | None = None,
) -> TilePlan:
    """Pure, deterministic planning function. Never touches the database,
    never calls Overpass, never mutates any existing scope/job row — it
    only computes a plan from its inputs and returns it (or raises
    TilePlannerError). Callers decide, in a future task, what to do with
    the returned TilePlan; this function has no side effects and is not
    wired into any existing import entrypoint."""
    if not city_slug or not str(city_slug).strip():
        raise TilePlannerError("city_slug is required")
    if not scope_code or not str(scope_code).strip():
        raise TilePlannerError("scope_code is required")
    if not profile or not str(profile).strip():
        raise TilePlannerError("profile is required")

    cfg = config or TilePlannerConfig()
    south, west, north, east = _validate_bbox(bbox)

    lat_span = north - south
    lng_span = east - west

    # Exact division: rows/cols are computed from ceil(span / max_size) so
    # every tile is <= the configured max, then each tile's actual size is
    # span / row_count (not the max) — this guarantees the grid EXACTLY
    # partitions the bbox with zero gap and zero overlap, rather than
    # tiling at a fixed max size and leaving an uneven remainder tile.
    rows = _ceil_div(lat_span, cfg.max_tile_height_deg)
    cols = _ceil_div(lng_span, cfg.max_tile_width_deg)

    total_tiles = rows * cols
    if total_tiles > cfg.max_tile_count:
        raise TilePlannerError(
            f"planned tile count {total_tiles} (rows={rows} x cols={cols}) exceeds "
            f"max_tile_count={cfg.max_tile_count}; narrow the bbox, increase "
            "max_tile_width_deg/max_tile_height_deg, or raise max_tile_count explicitly"
        )

    row_height = lat_span / rows
    col_width = lng_span / cols

    tiles: list[Tile] = []
    sequence = 0
    for row_index in range(rows):
        tile_south = south + row_index * row_height
        tile_north = north if row_index == rows - 1 else south + (row_index + 1) * row_height
        for col_index in range(cols):
            tile_west = west + col_index * col_width
            tile_east = east if col_index == cols - 1 else west + (col_index + 1) * col_width
            sequence += 1
            b_south, b_west, b_north, b_east = _round(tile_south), _round(tile_west), _round(tile_north), _round(tile_east)
            tiles.append(
                Tile(
                    tile_id=_tile_id(city_slug, scope_code, profile, b_south, b_west, b_north, b_east),
                    city_slug=city_slug,
                    scope_code=scope_code,
                    profile=profile,
                    south=b_south,
                    west=b_west,
                    north=b_north,
                    east=b_east,
                    sequence=sequence,
                    total_tiles=total_tiles,
                )
            )

    return TilePlan(
        city_slug=city_slug,
        scope_code=scope_code,
        profile=profile,
        original_bbox={"south": south, "west": west, "north": north, "east": east},
        tiles=tuple(tiles),
        planner_version=PLANNER_VERSION,
        rows=rows,
        cols=cols,
    )


def _ceil_div(span: float, max_size: float) -> int:
    if span <= 0:
        raise TilePlannerError(f"bbox span must be positive, got {span}")
    return max(1, math.ceil(round(span / max_size, COORDINATE_PRECISION)))
