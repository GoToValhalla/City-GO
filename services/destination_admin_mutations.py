from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination
from services.admin_audit_service import write_admin_audit_log
from services.destination_admin_queries import detail, require_destination
from services.destination_service import create_destination


def create(db: Session, data: dict[str, object], *, actor: str, action: str, context: dict[str, object] | None = None):
    if _slug_exists(db, str(data["slug"])):
        raise FileExistsError("Destination slug already exists")
    row = create_destination(db, data)
    write_admin_audit_log(db, actor=actor, action=action, entity_type="destination",
        entity_id=row.id, new_value=data | (context or {}))
    db.commit(); db.refresh(row)
    return detail(db, row.slug)


def update(db: Session, slug: str, data: dict[str, object], *, actor: str):
    destination = require_destination(db, slug)
    old = snapshot(destination)
    if "slug" in data and data["slug"] != destination.slug and _slug_exists(db, str(data["slug"])):
        raise FileExistsError("Destination slug already exists")
    for key, value in data.items():
        setattr(destination, key, value)
    write_admin_audit_log(db, actor=actor, action="destination_updated", entity_type="destination",
        entity_id=destination.id, old_value=old, new_value=snapshot(destination))
    db.commit(); db.refresh(destination)
    return detail(db, destination.slug)


def snapshot(destination: Destination) -> dict[str, object]:
    fields = ("slug", "name", "destination_type", "center_lat", "center_lng", "bbox",
        "launch_status", "is_published", "is_active")
    return {field: getattr(destination, field) for field in fields}


def _slug_exists(db: Session, slug: str) -> bool:
    return db.query(Destination.id).filter(Destination.slug == slug).first() is not None
