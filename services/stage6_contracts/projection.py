from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from services.published_snapshot_rebuild_service import rebuild_published_place_snapshots
from services.routing_projection_rebuild_service import rebuild_route_candidate_sets, rebuild_routing_place_nodes
from services.search_projection_rebuild_service import rebuild_search_place_documents


@dataclass(frozen=True)
class ProjectionRebuildCommand:
    projection_type: str
    city_id: int | None
    actor: str
    source: str
    audit_context: dict[str, object]


_BUILDERS: dict[str, Callable[..., dict[str, object]]] = {
    "published_place_snapshot": rebuild_published_place_snapshots,
    "search_place_document": rebuild_search_place_documents,
    "routing_place_node": rebuild_routing_place_nodes,
    "route_candidate_set": rebuild_route_candidate_sets,
}


def rebuild_projection(db: Session, command: ProjectionRebuildCommand) -> dict[str, object]:
    builder = _BUILDERS.get(command.projection_type)
    if builder is None:
        raise ValueError(f"Unsupported projection type: {command.projection_type}")
    return builder(
        db, city_id=command.city_id, actor=command.actor,
        source=command.source, audit_context=command.audit_context,
    )
