from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class PublicReadProjectionError(ValueError):
    """Contract failure for public projection reads; reason is HTTP-stable."""

    def __init__(self, message: str, *, reason: str = "projection_unavailable") -> None:
        super().__init__(message)
        self.reason = reason


FRESH_STATUS = "fresh"
STALE_STATUS = "stale"
REASON_EMPTY = "projection_empty"
REASON_STALE = "projection_stale"
REASON_MISSING = "projection_missing"
REASON_VERSION = "projection_version_incompatible"
REASON_INCOMPLETE = "projection_incomplete"
REASON_FAILED = "projection_rebuild_failed"
REASON_RUNNING = "projection_rebuild_running"
PUBLIC_READ_PATHS: tuple[str, ...] = ("public_catalog", "search", "routing")
PROJECTION_TYPES: tuple[str, ...] = ("search_place_document", "routing_place_node", "route_candidate_set")
REBUILD_JOB_STATUSES: tuple[str, ...] = ("queued", "running", "succeeded", "failed", "skipped")


@dataclass(frozen=True)
class PublicReadPathDecision:
    read_path: str
    projection_type: str
    uses_projection: bool
    fallback_allowed: bool
    reason: str


def is_projection_stale(
    *,
    source_snapshot_version: int | None,
    projection_snapshot_version: int | None,
    freshness_status: str | None = FRESH_STATUS,
) -> bool:
    if normalize_freshness_status(freshness_status) != FRESH_STATUS:
        return True
    if source_snapshot_version is None or projection_snapshot_version is None:
        return True
    return int(projection_snapshot_version) != int(source_snapshot_version)


def assert_projection_fresh(
    *,
    source_snapshot_version: int | None,
    projection_snapshot_version: int | None,
    freshness_status: str | None = FRESH_STATUS,
) -> None:
    if is_projection_stale(
        source_snapshot_version=source_snapshot_version,
        projection_snapshot_version=projection_snapshot_version,
        freshness_status=freshness_status,
    ):
        raise PublicReadProjectionError(
            "Public read projection is stale",
            reason=REASON_STALE,
        )


def choose_public_read_path(
    *,
    read_path: str,
    projection_type: str,
    projection_count: int,
    source_snapshot_version: int | None,
    projection_snapshot_version: int | None,
    freshness_status: str | None = FRESH_STATUS,
    fallback_allowed: bool = False,
) -> PublicReadPathDecision:
    normalized_read_path = normalize_read_path(read_path)
    normalized_projection_type = normalize_projection_type(projection_type)
    if int(projection_count) <= 0:
        if fallback_allowed:
            return PublicReadPathDecision(
                read_path=normalized_read_path,
                projection_type=normalized_projection_type,
                uses_projection=False,
                fallback_allowed=True,
                reason="projection_empty_fallback_allowed",
            )
        raise PublicReadProjectionError(
            "Public read projection is empty",
            reason=REASON_EMPTY,
        )
    assert_projection_fresh(
        source_snapshot_version=source_snapshot_version,
        projection_snapshot_version=projection_snapshot_version,
        freshness_status=freshness_status,
    )
    return PublicReadPathDecision(
        read_path=normalized_read_path,
        projection_type=normalized_projection_type,
        uses_projection=True,
        fallback_allowed=fallback_allowed,
        reason="projection_ready",
    )


def build_search_document_from_snapshot(
    *,
    snapshot: Mapping[str, object],
    locale: str = "default",
) -> dict[str, object]:
    assert_required_snapshot_fields(snapshot, ("place_id", "city_id", "snapshot_version"))
    is_public = bool(snapshot.get("is_public", snapshot.get("is_published", False)))
    is_search_visible = bool(snapshot.get("is_search_visible", snapshot.get("is_searchable", False)))
    title = snapshot.get("title")
    description = snapshot.get("description") or snapshot.get("summary") or ""
    category = snapshot.get("category")
    tags = snapshot.get("tags") or []
    searchable_parts = [str(part) for part in (title, description, category, " ".join(map(str, tags))) if part]
    return {
        "place_id": int(snapshot["place_id"]),
        "city_id": int(snapshot["city_id"]),
        "source_snapshot_version": int(snapshot["snapshot_version"]),
        "locale": locale,
        "title": str(title) if title is not None else None,
        "searchable_text": " ".join(searchable_parts).strip() or None,
        "category": str(category) if category is not None else None,
        "tags_payload": _search_metadata(snapshot, tags),
        "public_payload": dict(snapshot.get("public_payload") or {}),
        "is_public": is_public,
        "is_catalog_visible": is_public and bool(snapshot.get("is_catalog_visible", False)),
        "is_search_visible": is_public and is_search_visible,
        "ranking_score": float(snapshot.get("ranking_score", snapshot.get("quality_score", 0.0)) or 0.0),
        "freshness_status": FRESH_STATUS,
    }


def build_routing_node_from_snapshot(
    *,
    snapshot: Mapping[str, object],
    route_policy: str = "city_walking",
) -> dict[str, object]:
    assert_required_snapshot_fields(snapshot, ("place_id", "city_id", "snapshot_version", "lat", "lng"))
    is_public = bool(snapshot.get("is_public", snapshot.get("is_published", False)))
    is_route_visible = bool(snapshot.get("is_route_visible", snapshot.get("is_route_eligible", False)))
    return {
        "place_id": int(snapshot["place_id"]),
        "city_id": int(snapshot["city_id"]),
        "source_snapshot_version": int(snapshot["snapshot_version"]),
        "lat": float(snapshot["lat"]),
        "lng": float(snapshot["lng"]),
        "category": snapshot.get("category"),
        "route_policy": route_policy,
        "average_visit_duration_minutes": snapshot.get("average_visit_duration_minutes"),
        "is_route_visible": is_public and is_route_visible,
        "quality_score": int(snapshot.get("quality_score", 0) or 0),
        "place_payload": dict(snapshot.get("place_payload") or snapshot.get("public_payload") or {}),
        "freshness_status": FRESH_STATUS,
    }


def build_route_candidate_set(
    *,
    city_id: int,
    profile: str,
    route_policy: str,
    source_snapshot_version: int,
    routing_nodes: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    visible_nodes = [dict(node) for node in routing_nodes if bool(node.get("is_route_visible"))]
    candidate_ids = [int(node["place_id"]) for node in visible_nodes]
    return {
        "city_id": int(city_id),
        "profile": profile,
        "route_policy": route_policy,
        "source_snapshot_version": int(source_snapshot_version),
        "candidate_count": len(candidate_ids),
        "payload": {"place_ids": candidate_ids},
        "freshness_status": FRESH_STATUS,
    }


def build_projection_rebuild_summary(
    *,
    projection_type: str,
    source_snapshot_version: int | None,
    processed_count: int,
    rebuilt_count: int,
    skipped_count: int = 0,
    failed_count: int = 0,
    error_summary: str | None = None,
) -> dict[str, object]:
    normalized_projection_type = normalize_projection_type(projection_type)
    failed = int(failed_count)
    return {
        "projection_type": normalized_projection_type,
        "source_snapshot_version": source_snapshot_version,
        "processed_count": max(0, int(processed_count)),
        "rebuilt_count": max(0, int(rebuilt_count)),
        "skipped_count": max(0, int(skipped_count)),
        "failed_count": max(0, failed),
        "status": "failed" if failed > 0 else "succeeded",
        "error_summary": error_summary,
    }


def normalize_read_path(read_path: str) -> str:
    normalized = (read_path or "").strip().lower()
    if normalized not in PUBLIC_READ_PATHS:
        raise PublicReadProjectionError(f"Unsupported public read path: {read_path}")
    return normalized


def normalize_projection_type(projection_type: str) -> str:
    normalized = (projection_type or "").strip().lower()
    if normalized not in PROJECTION_TYPES:
        raise PublicReadProjectionError(f"Unsupported projection type: {projection_type}")
    return normalized


def normalize_freshness_status(freshness_status: str | None) -> str:
    return (freshness_status or "").strip().lower()


def assert_required_snapshot_fields(snapshot: Mapping[str, object], required_fields: Sequence[str]) -> None:
    missing = [field for field in required_fields if snapshot.get(field) is None]
    if missing:
        raise PublicReadProjectionError(f"Missing snapshot fields: {missing}")


def _search_metadata(snapshot: Mapping[str, object], tags: object) -> dict[str, object]:
    metadata: dict[str, object] = {"tags": list(tags) if isinstance(tags, list) else tags}
    optional = {
        "tag_ids": list(snapshot.get("tag_ids") or []),
        "category_id": snapshot.get("category_id"),
        "destination_ids": list(snapshot.get("destination_ids") or []),
    }
    return metadata | {key: value for key, value in optional.items() if value not in (None, [])}
