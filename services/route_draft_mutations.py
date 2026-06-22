from __future__ import annotations

from sqlalchemy.orm import Session

from models.route_draft import RouteDraft, RouteDraftPoint
from services.route_draft_errors import RouteDraftError
from services.route_draft_loader import check_version, eligible_place_or_error, point_or_error, route_place_ids
from services.route_draft_recalc import recalculate_draft
from services.route_draft_rules import visit_minutes_for, warning


def remove_point(db: Session, draft: RouteDraft, point_id: int, version: int) -> RouteDraft:
    check_version(draft, version)
    point = point_or_error(draft, point_id)
    if point.user_locked:
        raise RouteDraftError("PLACE_IS_LOCKED", "Locked point cannot be removed", 400)
    draft.user_removed_place_ids = sorted(set(draft.user_removed_place_ids or []) | {int(point.place_id)})
    draft.points = [item for item in draft.points if item.id != point_id]
    db.delete(point)
    db.flush()
    _touch(draft, "remove_point", {"place_id": point.place_id})
    if not draft.points:
        draft.warnings = _append_warning(draft, "LAST_POINT_REMOVED", "Все точки удалены из маршрута.")
    return _save(db, draft)


def add_point(db: Session, draft: RouteDraft, place_id: int, after_position: int | None, version: int, allow_readd: bool) -> RouteDraft:
    check_version(draft, version)
    if place_id in route_place_ids(draft):
        raise RouteDraftError("PLACE_ALREADY_IN_ROUTE", "Place is already in draft", 400)
    if not allow_readd and place_id in set(draft.user_removed_place_ids or []):
        raise RouteDraftError("PLACE_WAS_REMOVED", "Removed place requires allow_readd=true", 400)
    place = eligible_place_or_error(db, draft.city_id, place_id)
    position = _insert_position(draft, after_position)
    _shift_points(draft, position)
    db.add(RouteDraftPoint(place=place, place_id=place.id, draft_id=draft.id, position=position, inserted_by_user=True, visit_minutes=visit_minutes_for(place)))
    db.flush()
    _touch(draft, "add_point", {"place_id": place.id})
    return _save(db, _warn_over_budget(recalculate_draft(draft)))


def replace_point(db: Session, draft: RouteDraft, point_id: int, replacement_place_id: int, version: int) -> RouteDraft:
    check_version(draft, version)
    point = point_or_error(draft, point_id)
    if replacement_place_id in route_place_ids(draft):
        raise RouteDraftError("PLACE_ALREADY_IN_ROUTE", "Replacement is already in draft", 400)
    place = eligible_place_or_error(db, draft.city_id, replacement_place_id)
    old_place_id = int(point.place_id)
    point.place_id = place.id
    point.place = place
    point.inserted_by_user = True
    point.replacement_of_place_id = old_place_id
    point.visit_minutes = visit_minutes_for(place)
    draft.user_removed_place_ids = sorted(set(draft.user_removed_place_ids or []) | {old_place_id})
    _touch(draft, "replace_point", {"old_place_id": old_place_id, "place_id": place.id})
    return _save(db, draft)


def _insert_position(draft: RouteDraft, after_position: int | None) -> int:
    if after_position is None:
        return len(draft.points) + 1
    return max(1, int(after_position) + 1)


def _shift_points(draft: RouteDraft, position: int) -> None:
    for point in draft.points:
        if point.position >= position:
            point.position += 1


def _touch(draft: RouteDraft, action: str, payload: dict[str, object]) -> None:
    draft.edit_history = list(draft.edit_history or []) + [{"action": action, **payload}]
    draft.version += 1


def _save(db: Session, draft: RouteDraft) -> RouteDraft:
    recalculate_draft(draft)
    db.commit()
    db.refresh(draft)
    return draft


def _append_warning(draft: RouteDraft, code: str, message: str) -> list[dict[str, str]]:
    return list(draft.warnings or []) + [warning(code, message)]


def _warn_over_budget(draft: RouteDraft) -> RouteDraft:
    if draft.total_minutes > draft.budget_minutes:
        draft.warnings = _append_warning(draft, "OVER_BUDGET", "Маршрут вышел за выбранный лимит времени.")
    return draft
