"""Задачи обновления адресов из админки."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.admin_operation import AdminOperation
from models.city import City
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.place_address_geocode import format_nominatim_address, reverse_geocode_payload
from services.place_address_recovery_assess import assess_proposed_address
from services.product_event_service import record_event
from services.system_log_service import write_system_log


def queue_address_refresh(
    db: Session, *, actor: str, city_slug: str | None = None, place_ids: list[int] | None = None,
) -> AdminOperation:
    op = AdminOperation(
        operation_type="address_refresh", status="running", actor=actor,
        city_slug=city_slug, place_ids=place_ids or [],
    )
    db.add(op)
    db.flush()
    try:
        result = _run_refresh(db, city_slug=city_slug, place_ids=place_ids or [])
        op.status = "completed"
        op.result = result
        record_event(db, event_type="address_updated", payload=result, city_slug=city_slug, commit=False)
    except Exception as exc:  # noqa: BLE001
        op.status = "failed"
        op.error_message = str(exc)
        write_system_log(db, level="error", module="address_refresh", message=str(exc),
                         city_slug=city_slug, commit=False)
    op.updated_at = datetime.utcnow()
    write_admin_audit_log(db, actor=actor, action="address_refresh", entity_type="admin_operation",
                          entity_id=op.id, new_value={"status": op.status, "city_slug": city_slug})
    db.commit()
    db.refresh(op)
    return op


def _run_refresh(db: Session, *, city_slug: str | None, place_ids: list[int]) -> dict[str, object]:
    query = db.query(Place)
    if place_ids:
        query = query.filter(Place.id.in_(place_ids))
    elif city_slug:
        city = db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            raise ValueError("Город не найден")
        query = query.filter(Place.city_id == city.id)
    else:
        raise ValueError("Укажите город или места")
    applied, skipped, errors = 0, 0, 0
    for place in query.limit(200).all():
        city = db.query(City).filter(City.id == place.city_id).first()
        try:
            if _refresh_one(db, place, city.name if city else "", city.slug if city else ""):
                applied += 1
            else:
                skipped += 1
        except Exception:
            errors += 1
    return {"applied": applied, "skipped": skipped, "errors": errors}


def _refresh_one(db: Session, place: Place, city_name: str, city_slug: str) -> bool:
    payload = reverse_geocode_payload(float(place.lat), float(place.lng))
    proposed = format_nominatim_address(payload)
    assessment = assess_proposed_address(proposed, place.category, city_name=city_name, city_slug=city_slug)
    if not assessment.get("should_apply"):
        return False
    place.address = str(proposed)
    place.address_source = "nominatim"
    conf_map = {"high": 0.9, "medium": 0.7, "medium-low": 0.5, "low": 0.3, "none": 0.0}
    raw = str(assessment.get("confidence") or "medium")
    place.address_confidence = conf_map.get(raw, 0.7)
    place.address_updated_at = datetime.utcnow()
    return True
