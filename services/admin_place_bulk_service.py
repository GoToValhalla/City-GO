"""Массовые действия по местам: preview и apply."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.admin_place_update_service import update_admin_place_fields
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_publication_eligibility import place_publication_eligibility
from services.place_verification_mutation import verify_locked_place
from services.product_event_service import record_event
from services.publication_state_writer import (
    REASON_ADMIN_HIDE,
    REASON_NEEDS_MANUAL_REVIEW,
    transition_place_publication,
)

DANGEROUS = frozenset({"publish", "hide", "set_category", "disable_route", "remove_tags"})


def preview_bulk(db: Session, place_ids: list[int], action: str, params: dict[str, object]) -> dict[str, object]:
    places = db.query(Place).filter(Place.id.in_(place_ids)).order_by(Place.id.asc()).all()
    cities = {c.id: c.name for c in db.query(City).filter(City.id.in_({p.city_id for p in places})).all()}
    cats: dict[str, int] = {}
    for place in places:
        key = place.category or "unknown"
        cats[key] = cats.get(key, 0) + 1
    payload: dict[str, object] = {
        "action": action,
        "total": len(places),
        "place_ids": [place.id for place in places],
        "cities": [
            {
                "city_id": city_id,
                "name": cities.get(city_id, "?"),
                "count": sum(1 for place in places if place.city_id == city_id),
            }
            for city_id in sorted({place.city_id for place in places})
        ],
        "categories": cats,
        "field_changes": _describe(action, params),
        "is_dangerous": action in DANGEROUS,
        "risks": _risks(action, len(places)),
    }
    if action in {"publish", "enable_visible"}:
        eligible_ids: list[int] = []
        blocked: list[dict[str, object]] = []
        for place in places:
            eligibility = place_publication_eligibility(place)
            if eligibility.eligible:
                eligible_ids.append(place.id)
            else:
                blocked.append({"place_id": place.id, "reasons": list(eligibility.reasons)})
        payload["would_publish_place_ids"] = eligible_ids
        payload["would_block_place_ids"] = [row["place_id"] for row in blocked]
        payload["blocked_reasons"] = blocked
    return payload


def apply_bulk(
    db: Session,
    place_ids: list[int],
    action: str,
    params: dict[str, object],
    *,
    actor: str,
) -> dict[str, object]:
    unique_ids = sorted({int(place_id) for place_id in place_ids})
    locked_places = (
        db.query(Place)
        .filter(Place.id.in_(unique_ids))
        .order_by(Place.id.asc())
        .with_for_update()
        .populate_existing()
        .all()
    )
    places_by_id = {int(place.id): place for place in locked_places}
    errors: list[dict[str, object]] = []
    applied = 0

    try:
        for place_id in unique_ids:
            place = places_by_id.get(place_id)
            if place is None:
                errors.append({"place_id": place_id, "error": "Место не найдено"})
                continue
            try:
                with db.begin_nested():
                    _apply_one_locked(db, place, action, params, actor=actor)
                applied += 1
            except Exception as exc:  # noqa: BLE001 - truthful per-row bulk result
                errors.append({"place_id": place_id, "error": str(exc)})

        write_admin_audit_log(
            db,
            actor=actor,
            action=f"bulk_{action}",
            entity_type="place",
            entity_id=",".join(str(item) for item in unique_ids[:20]),
            new_value={"ok": applied, "errors": len(errors), "action": action},
            reason=params.get("reason"),
        )
        record_event(
            db,
            event_type="place_bulk_action",
            payload={"action": action, "ok": applied, "errors": len(errors)},
            commit=False,
        )
        db.commit()
        return {"applied": applied, "failed": len(errors), "errors": errors}
    except Exception:
        db.rollback()
        raise


def _apply_one_locked(
    db: Session,
    place: Place,
    action: str,
    params: dict[str, object],
    *,
    actor: str,
) -> None:
    reason = str(params.get("reason") or "bulk")
    if action in {"publish", "enable_visible"}:
        if place.publication_status == "published" and place.is_published and place.is_visible_in_catalog:
            raise ValueError("Место уже опубликовано")
        eligibility = place_publication_eligibility(place)
        if not eligibility.eligible:
            raise ValueError("Публикация заблокирована: " + ", ".join(eligibility.reasons))
        apply_admin_city_publication_place(
            db,
            place,
            actor=actor,
            source=f"admin_bulk_{action}",
            reason=reason,
            lock_place=False,
        )
        return
    if action in {"hide", "disable_visible"}:
        if not place.is_published and not place.is_visible_in_catalog:
            raise ValueError("Место уже скрыто")
        transition_place_publication(
            db,
            place,
            to_status="hidden",
            reason_code=REASON_ADMIN_HIDE,
            actor=actor,
            source=f"admin_bulk_{action}",
            reason_details={"bulk_action": action},
            human_comment=reason,
            lock_place=False,
        )
        return
    if action == "send_review":
        if place.publication_status in {"needs_review", "needs_manual_review"}:
            raise ValueError("Место уже находится на ручной проверке")
        transition_place_publication(
            db,
            place,
            to_status="needs_review",
            reason_code=REASON_NEEDS_MANUAL_REVIEW,
            actor=actor,
            source="admin_bulk_send_review",
            reason_details={"bulk_action": action},
            human_comment=reason,
            lock_place=False,
        )
        return
    if action in {"enable_route", "disable_route"}:
        if place.publication_status != "published" or not place.is_published:
            raise ValueError("Маршрутный статус можно менять только у опубликованного места")
        target = action == "enable_route"
        if bool(place.is_route_eligible) is target:
            raise ValueError("Маршрутный статус уже установлен")
        apply_admin_city_publication_place(
            db,
            place,
            actor=actor,
            source=f"admin_bulk_{action}",
            reason=reason,
            lock_place=False,
            route_eligible_override=target,
        )
        return
    if action == "verify":
        verify_locked_place(
            db,
            place,
            actor=actor,
            reason=reason,
            action="bulk_verify_place",
            reject_noop=True,
            lock_place=False,
        )
        return
    if action == "set_category":
        new_category = str(params["category"]).strip().lower()
        current_category = str(place.canonical_category or place.category or "").strip().lower()
        if current_category == new_category:
            raise ValueError("Категория уже установлена")
        update_admin_place_fields(
            db,
            int(place.id),
            {"category": new_category},
            actor=actor,
            commit=False,
            locked_place=place,
        )
        return
    if action in {"add_tags", "remove_tags"}:
        existing = {
            row.tag_id for row in db.query(PlaceTag).filter(PlaceTag.place_id == place.id).all()
        }
        requested = {int(tag_id) for tag_id in params.get("tag_ids") or []}
        if action == "add_tags":
            target = existing | requested
            if target == existing:
                raise ValueError("Все выбранные теги уже добавлены")
        else:
            target = existing - requested
            if target == existing:
                raise ValueError("Выбранные теги отсутствуют")
        update_admin_place_fields(
            db,
            int(place.id),
            {"tag_ids": sorted(target)},
            actor=actor,
            commit=False,
            locked_place=place,
        )
        return
    raise ValueError(f"Неизвестное действие: {action}")


def _describe(action: str, params: dict[str, object]) -> list[dict[str, str]]:
    mapping = {
        "set_category": [("category", "→", str(params.get("category", "")))],
        "disable_route": [("is_route_eligible", "true", "false")],
        "enable_route": [("is_route_eligible", "false", "true")],
        "enable_visible": [("publication_status", "*", "published")],
        "disable_visible": [("publication_status", "*", "hidden")],
        "publish": [("publication_status", "*", "published")],
        "hide": [("publication_status", "*", "hidden")],
        "send_review": [("publication_status", "*", "needs_review")],
    }
    return [{"field": field, "from": old, "to": new} for field, old, new in mapping.get(action, [])]


def _risks(action: str, count: int) -> str:
    if count > 50 and action in DANGEROUS:
        return f"Массовое изменение {count} мест — проверьте preview"
    return ""
