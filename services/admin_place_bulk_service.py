"""Массовые действия по местам: preview и apply."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.admin_place_update_service import update_admin_place_fields
from services.admin_service import publish_place, unpublish_place, verify_place
from services.product_event_service import record_event

DANGEROUS = frozenset({"publish", "hide", "set_category", "disable_route", "remove_tags"})


def preview_bulk(db: Session, place_ids: list[int], action: str, params: dict[str, object]) -> dict[str, object]:
    places = db.query(Place).filter(Place.id.in_(place_ids)).all()
    cities = {c.id: c.name for c in db.query(City).filter(City.id.in_({p.city_id for p in places})).all()}
    cats: dict[str, int] = {}
    for p in places:
        key = p.category or "unknown"
        cats[key] = cats.get(key, 0) + 1
    changes = _describe(action, params)
    return {
        "action": action, "total": len(places), "place_ids": [p.id for p in places],
        "cities": [{"city_id": cid, "name": cities.get(cid, "?"), "count": sum(1 for p in places if p.city_id == cid)}
                   for cid in sorted({p.city_id for p in places})],
        "categories": cats, "field_changes": changes,
        "is_dangerous": action in DANGEROUS, "risks": _risks(action, len(places)),
    }


def apply_bulk(db: Session, place_ids: list[int], action: str, params: dict[str, object], *, actor: str) -> dict[str, object]:
    ok, errors = 0, []
    for pid in place_ids:
        try:
            _apply_one(db, pid, action, params, actor=actor)
            ok += 1
        except Exception as exc:  # noqa: BLE001 — partial errors for bulk
            errors.append({"place_id": pid, "error": str(exc)})
    write_admin_audit_log(db, actor=actor, action=f"bulk_{action}", entity_type="place",
                          entity_id=",".join(str(i) for i in place_ids[:20]),
                          new_value={"ok": ok, "errors": len(errors), "action": action}, reason=params.get("reason"))
    record_event(db, event_type="place_bulk_action", payload={"action": action, "ok": ok, "errors": len(errors)})
    db.commit()
    return {"applied": ok, "failed": len(errors), "errors": errors}


def _apply_one(db: Session, place_id: int, action: str, params: dict[str, object], *, actor: str) -> None:
    handlers = {
        "publish": lambda: publish_place(db, place_id, actor=actor, reason=str(params.get("reason") or "bulk")),
        "hide": lambda: unpublish_place(db, place_id, actor=actor, reason=str(params.get("reason") or "bulk hide")),
        "verify": lambda: verify_place(db, place_id, actor=actor),
        "send_review": lambda: update_admin_place_fields(db, place_id, {"publication_status": "needs_review"}, actor=actor),
        "set_category": lambda: update_admin_place_fields(db, place_id, {"category": params["category"]}, actor=actor),
        "enable_route": lambda: update_admin_place_fields(db, place_id, {"is_route_eligible": True, "route_exclusion_reason": None}, actor=actor),
        "disable_route": lambda: update_admin_place_fields(db, place_id, {"is_route_eligible": False, "route_exclusion_reason": params.get("reason")}, actor=actor),
        "enable_visible": lambda: update_admin_place_fields(db, place_id, {"is_visible_in_catalog": True}, actor=actor),
        "disable_visible": lambda: update_admin_place_fields(db, place_id, {"is_visible_in_catalog": False}, actor=actor),
        "add_tags": lambda: _add_tags(db, place_id, params.get("tag_ids") or []),
        "remove_tags": lambda: _remove_tags(db, place_id, params.get("tag_ids") or []),
    }
    fn = handlers.get(action)
    if fn is None:
        raise ValueError(f"Неизвестное действие: {action}")
    fn()


def _add_tags(db: Session, place_id: int, tag_ids: list[object]) -> None:
    existing = {r.tag_id for r in db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()}
    for tid in tag_ids:
        if int(tid) not in existing:
            db.add(PlaceTag(place_id=place_id, tag_id=int(tid)))


def _remove_tags(db: Session, place_id: int, tag_ids: list[object]) -> None:
    ids = [int(t) for t in tag_ids]
    db.query(PlaceTag).filter(PlaceTag.place_id == place_id, PlaceTag.tag_id.in_(ids)).delete()


def _describe(action: str, params: dict[str, object]) -> list[dict[str, str]]:
    mapping = {
        "set_category": [("category", "→", str(params.get("category", "")))],
        "disable_route": [("is_route_eligible", "true", "false")],
        "enable_route": [("is_route_eligible", "false", "true")],
        "enable_visible": [("is_visible_in_catalog", "false", "true")],
        "disable_visible": [("is_visible_in_catalog", "true", "false")],
        "publish": [("publication_status", "*", "published")],
        "hide": [("publication_status", "*", "hidden")],
    }
    return [{"field": a, "from": b, "to": c} for a, b, c in mapping.get(action, [])]


def _risks(action: str, count: int) -> str:
    if count > 50 and action in DANGEROUS:
        return f"Массовое изменение {count} мест — проверьте preview"
    return ""
