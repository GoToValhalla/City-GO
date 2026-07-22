"""Safety gate for enabling Stage 5 read toggles."""

from sqlalchemy.orm import Session

from services.projection_readiness_service import assert_projection_ready

TOGGLE_PROJECTIONS = {
    "search_projection_reads_enabled": ("search_place_document",),
    "catalog_projection_reads_enabled": ("search_place_document",),
    "routing_projection_reads_enabled": ("routing_place_node", "route_candidate_set"),
}


def assert_toggle_activation_safe(db: Session, key: str) -> None:
    kinds = TOGGLE_PROJECTIONS.get(key)
    if not kinds:
        return
    for kind in kinds:
        assert_projection_ready(db, projection_type=kind, city_id=None)
