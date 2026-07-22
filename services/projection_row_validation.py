"""Physical row validation for a ready Stage 5 generation."""

from sqlalchemy.orm import Session

from models.search_routing_stage5 import RouteCandidateSet, RoutingPlaceNode, SearchPlaceDocument
from services.public_read_projection_service import PublicReadProjectionError, REASON_EMPTY, REASON_INCOMPLETE, REASON_STALE, REASON_VERSION
from services.projection_snapshot_source import latest_published_snapshots


def assert_projection_rows(db: Session, status: object) -> None:
    snapshots = latest_published_snapshots(db, city_id=status.city_id)
    if not snapshots:
        return
    if status.projection_type == "search_place_document":
        query = db.query(SearchPlaceDocument)
        if status.city_id is not None:
            query = query.filter(SearchPlaceDocument.city_id == status.city_id)
        _assert_place_rows(snapshots, query.order_by(SearchPlaceDocument.source_snapshot_version.desc()).all())
    elif status.projection_type == "routing_place_node":
        query = db.query(RoutingPlaceNode)
        if status.city_id is not None:
            query = query.filter(RoutingPlaceNode.city_id == status.city_id)
        _assert_place_rows(snapshots, query.order_by(RoutingPlaceNode.source_snapshot_version.desc()).all())
    elif status.projection_type == "route_candidate_set":
        _assert_candidate_sets(db, status, snapshots)


def _assert_candidate_sets(db: Session, status: object, snapshots: list[object]) -> None:
    query = db.query(RouteCandidateSet)
    if status.city_id is not None:
        query = query.filter(RouteCandidateSet.city_id == status.city_id)
    rows = query.filter(RouteCandidateSet.freshness_status == "fresh").all()
    expected = {int(row.city_id) for row in snapshots}
    if {int(row.city_id) for row in rows} != expected or any(row.source_snapshot_version != status.projection_version for row in rows):
        raise PublicReadProjectionError("Route candidate sets are incomplete", reason=REASON_INCOMPLETE)
    if any(bool(row.is_route_visible) for row in snapshots) and sum(int(row.candidate_count) for row in rows) == 0:
        raise PublicReadProjectionError("Route candidate sets are empty", reason=REASON_EMPTY)


def _assert_place_rows(snapshots: list[object], rows: list[object]) -> None:
    latest = {int(row.place_id): row for row in reversed(rows)}
    if len(latest) != len(snapshots):
        raise PublicReadProjectionError("Projection record count is incomplete", reason=REASON_INCOMPLETE)
    if any(latest.get(int(snapshot.place_id)) is None or latest[int(snapshot.place_id)].source_snapshot_version != snapshot.snapshot_version for snapshot in snapshots):
        raise PublicReadProjectionError("Projection version is incompatible", reason=REASON_VERSION)
    if any(row.freshness_status != "fresh" for row in latest.values()):
        raise PublicReadProjectionError("Projection is stale", reason=REASON_STALE)
