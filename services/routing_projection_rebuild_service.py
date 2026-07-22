"""Atomic Stage 5 routing-node and candidate-set rebuilds."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from models.search_routing_stage5 import ProjectionRebuildJob, RouteCandidateSet, RoutingPlaceNode
from services.projection_snapshot_source import latest_published_snapshots, source_version
from services.public_read_projection_service import build_route_candidate_set, build_routing_node_from_snapshot
from services.projection_rebuild_lock import serialize_projection_rebuilds


def rebuild_routing_place_nodes(db: Session, *, city_id: int | None = None, actor: str = "system", source: str = "projection_rebuild", audit_context: dict[str, object] | None = None) -> dict[str, object]:
    serialize_projection_rebuilds(db)
    duplicate = _running(db, "routing_place_node", city_id)
    if duplicate:
        return _summary(duplicate, "skipped")
    snapshots = latest_published_snapshots(db, city_id=city_id)
    job = _start(db, "routing_place_node", city_id, len(snapshots), source_version(snapshots), actor, source, audit_context)
    nodes = [_node_payload(row) for row in snapshots if _has_coordinates(row)]
    if len(nodes) != len(snapshots):
        return _finish(db, job, len(nodes), complete=False)
    query = db.query(RoutingPlaceNode)
    if city_id is not None:
        query = query.filter(RoutingPlaceNode.city_id == city_id)
    query.delete(synchronize_session=False)
    db.add_all([RoutingPlaceNode(**payload) for payload in nodes])
    return _finish(db, job, len(nodes), complete=len(nodes) == len(snapshots))


def rebuild_route_candidate_sets(db: Session, *, city_id: int | None = None, actor: str = "system", source: str = "projection_rebuild", audit_context: dict[str, object] | None = None) -> dict[str, object]:
    serialize_projection_rebuilds(db)
    duplicate = _running(db, "route_candidate_set", city_id)
    if duplicate:
        return _summary(duplicate, "skipped")
    snapshots = latest_published_snapshots(db, city_id=city_id)
    version = source_version(snapshots)
    nodes_query = db.query(RoutingPlaceNode).filter(RoutingPlaceNode.freshness_status == "fresh")
    if city_id is not None:
        nodes_query = nodes_query.filter(RoutingPlaceNode.city_id == city_id)
    nodes = list(nodes_query.order_by(RoutingPlaceNode.city_id, RoutingPlaceNode.place_id).all())
    city_ids = sorted({int(row.city_id) for row in snapshots})
    job = _start(db, "route_candidate_set", city_id, len(city_ids), version, actor, source, audit_context)
    target = db.query(RouteCandidateSet)
    if city_id is not None:
        target = target.filter(RouteCandidateSet.city_id == city_id)
    target.delete(synchronize_session=False)
    payloads = [build_route_candidate_set(city_id=value, profile="overview", route_policy="city_walking", source_snapshot_version=int(version or 0), routing_nodes=[_node_dict(row) for row in nodes if row.city_id == value]) for value in city_ids]
    db.add_all([RouteCandidateSet(**payload) for payload in payloads])
    complete = all(int(payload["candidate_count"]) == len([row for row in nodes if row.city_id == payload["city_id"] and row.is_route_visible]) for payload in payloads)
    return _finish(db, job, len(payloads), complete=complete)


def _node_payload(snapshot) -> dict[str, object]:
    payload, quality = snapshot.snapshot_payload or {}, snapshot.quality_payload or {}
    place_payload = dict(payload.get("route_payload") or {}) | {"destination_ids": payload.get("destination_ids") or []}
    return build_routing_node_from_snapshot(snapshot={"place_id": snapshot.place_id, "city_id": snapshot.city_id, "snapshot_version": snapshot.snapshot_version, "lat": payload.get("lat"), "lng": payload.get("lng"), "category": payload.get("canonical_category") or payload.get("category"), "average_visit_duration_minutes": payload.get("average_visit_duration_minutes"), "is_public": snapshot.is_public, "is_route_visible": snapshot.is_route_visible, "quality_score": quality.get("quality_score", 0), "place_payload": place_payload})


def _node_dict(row: RoutingPlaceNode) -> dict[str, object]:
    return {"place_id": row.place_id, "is_route_visible": row.is_route_visible}


def _has_coordinates(row) -> bool:
    payload = row.snapshot_payload or {}
    return payload.get("lat") is not None and payload.get("lng") is not None


def _running(db: Session, kind: str, city_id: int | None):
    return db.query(ProjectionRebuildJob).filter(ProjectionRebuildJob.projection_type == kind, ProjectionRebuildJob.city_id.is_(None) if city_id is None else ProjectionRebuildJob.city_id == city_id, ProjectionRebuildJob.status.in_(("queued", "running"))).first()


def _start(db, kind, city_id, expected, version, actor, source, context):
    job = ProjectionRebuildJob(projection_type=kind, city_id=city_id, scope_key="global" if city_id is None else f"city:{city_id}", status="running", generation=uuid4().hex, source_snapshot_version=version, expected_count=expected, actor=actor, source=source, audit_context=context or {}, started_at=datetime.now(timezone.utc))
    db.add(job); db.flush(); return job


def _finish(db, job, actual, *, complete):
    job.processed_count = job.expected_count; job.rebuilt_count = actual; job.actual_count = actual; job.is_complete = complete; job.status = "succeeded" if complete else "failed"; job.failed_count = 0 if complete else max(1, job.expected_count - actual); job.error_summary = None if complete else "projection_incomplete"; job.finished_at = datetime.now(timezone.utc); db.flush(); return _summary(job, job.status)


def _summary(job, status):
    return {"job_id": job.id, "projection_type": job.projection_type, "status": status, "source_snapshot_version": job.source_snapshot_version, "processed_count": job.processed_count, "rebuilt_count": job.rebuilt_count, "expected_count": job.expected_count, "actual_count": job.actual_count, "generation": job.generation, "is_complete": job.is_complete, "skipped_count": 1 if status == "skipped" else 0, "failed_count": job.failed_count, "error_summary": job.error_summary}
