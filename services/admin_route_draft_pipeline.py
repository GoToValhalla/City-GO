"""Admin pipeline for saving dry-run routes as drafts and publishing them."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.route import Route
from models.route_place import RoutePlace
from schemas.admin_route_dry_run import AdminRouteDraftPublishRequest, AdminRouteDryRunRequest
from services.admin_audit_service import write_admin_audit_log
from services.admin_route_draft_helpers import build_admin_draft, city_or_404, places_by_id, route_payload, unique_route_slug
from services.admin_route_dry_run_service import AdminRouteDryRunService
from services.route_draft_loader import get_draft_or_error
from services.route_draft_recalc import recalculate_draft
from services.route_draft_rules import warning
from services.route_draft_serializer import serialize_draft
from services.route_random_select import point_for_place


def generate_admin_route_draft(db: Session, request: AdminRouteDryRunRequest, actor_id: str) -> dict[str, object]:
    city = city_or_404(db, request.city_slug)
    dry_run = AdminRouteDryRunService().run(db, request=request, actor_id=actor_id)
    selected_ids = [item.place_id for item in dry_run.selected_places]
    if not selected_ids:
        raise HTTPException(status_code=422, detail={"code": "NOT_ENOUGH_ELIGIBLE_PLACES"})
    places = places_by_id(db, selected_ids)
    draft = build_admin_draft(city, request)
    db.add(draft)
    db.flush()
    draft.points = [point_for_place(places[place_id], index) for index, place_id in enumerate(selected_ids, start=1)]
    draft.warnings = [] if dry_run.counts.selected_places >= 2 else [
        warning("ADMIN_DRAFT_PARTIAL", "Draft route has fewer than two selected places.")
    ]
    recalculate_draft(draft)
    write_admin_audit_log(
        db,
        actor=actor_id,
        action="generate_route_draft",
        entity_type="route_draft",
        entity_id=draft.id,
        new_value={"city_slug": city.slug, "generation_run_id": dry_run.generation_run_id},
    )
    db.commit()
    db.refresh(draft)
    return {"draft": serialize_draft(draft), "dry_run": dry_run}


def publish_admin_route_draft(
    db: Session,
    *,
    draft_id: int,
    payload: AdminRouteDraftPublishRequest,
    actor_id: str,
) -> dict[str, object]:
    draft = get_draft_or_error(db, draft_id)
    points = sorted(draft.points, key=lambda item: item.position)
    if not points:
        raise HTTPException(status_code=422, detail={"code": "DRAFT_HAS_NO_POINTS"})
    route = Route(
        city_id=draft.city_id,
        slug=unique_route_slug(db, payload.slug or f"{draft.city.slug}-route-{draft.id}"),
        title=payload.title or f"Маршрут по городу {draft.city.name}",
        short_description="Собран из draft route в админке.",
        duration_minutes=draft.total_minutes,
        route_mode="walk",
        is_active=True,
    )
    db.add(route)
    db.flush()
    route.route_places = [RoutePlace(route_id=route.id, place_id=point.place_id, position=index) for index, point in enumerate(points, start=1)]
    old_status = draft.status
    draft.status = "published"
    draft.edit_history = [*(draft.edit_history or []), {"action": "publish", "route_id": route.id}]
    write_admin_audit_log(
        db,
        actor=actor_id,
        action="publish_route_draft",
        entity_type="route",
        entity_id=route.id,
        old_value={"draft_status": old_status},
        new_value={"draft_id": draft.id, "route_slug": route.slug},
        reason=payload.reason,
    )
    db.commit()
    db.refresh(route)
    return {"draft_id": draft.id, "route": route_payload(route), "message": "Маршрут опубликован"}
