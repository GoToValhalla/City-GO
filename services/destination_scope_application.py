from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import DestinationScope
from services.admin_audit_service import write_admin_audit_log
from services.destination_admin_queries import require_destination
from services.destination_data_pipeline_service import active_destination_run
from services.destination_geo_candidate_service import recover_or_create_scope


def create(db: Session, slug: str, data: dict[str, object], *, actor: str):
    destination = require_destination(db, slug)
    if code_exists(db, destination.id, str(data["code"])):
        raise FileExistsError("Scope code already exists")
    scope = DestinationScope(destination_id=destination.id, **data)
    db.add(scope)
    write_admin_audit_log(db, actor=actor, action="destination_scope_created",
        entity_type="destination_scope", entity_id=None,
        new_value=data | {"destination_id": destination.id})
    db.commit(); db.refresh(scope)
    return scope


def recover(db: Session, slug: str, candidate, payload, *, actor: str):
    destination = require_destination(db, slug)
    scope, action = recover_or_create_scope(db, destination, candidate, code=payload.code,
        name=payload.name, import_profile=payload.import_profile, enabled=payload.enabled,
        recover=payload.recover)
    write_admin_audit_log(db, actor=actor, action=f"destination_scope_{action}_from_geo",
        entity_type="destination_scope", entity_id=scope.id,
        new_value=snapshot(scope) | {"candidate_key": candidate.candidate_key})
    db.commit(); db.refresh(scope)
    return {"scope": scope, "action": action}


def update(db: Session, slug: str, scope_id: int, data: dict[str, object], *, actor: str):
    destination = require_destination(db, slug)
    scope = require_scope(db, destination.id, scope_id)
    old = snapshot(scope)
    if "code" in data and data["code"] != scope.code and code_exists(db, destination.id, str(data["code"])):
        raise FileExistsError("Scope code already exists")
    for key, value in data.items():
        setattr(scope, key, value)
    write_admin_audit_log(db, actor=actor, action="destination_scope_updated",
        entity_type="destination_scope", entity_id=scope.id, old_value=old, new_value=snapshot(scope))
    db.commit(); db.refresh(scope)
    return scope


def delete(db: Session, slug: str, scope_id: int, *, actor: str) -> dict[str, bool]:
    destination = require_destination(db, slug)
    scope = require_scope(db, destination.id, scope_id)
    if active_destination_run(db, destination.id) is not None:
        raise RuntimeError("Нельзя удалить контур во время активного прогона")
    old = snapshot(scope)
    db.delete(scope)
    write_admin_audit_log(db, actor=actor, action="destination_scope_deleted",
        entity_type="destination_scope", entity_id=scope.id, old_value=old)
    db.commit()
    return {"deleted": True}


def require_scope(db: Session, destination_id: int, scope_id: int) -> DestinationScope:
    scope = db.query(DestinationScope).filter_by(destination_id=destination_id, id=scope_id).first()
    if scope is None:
        raise LookupError("Scope not found")
    return scope


def code_exists(db: Session, destination_id: int, code: str) -> bool:
    return db.query(DestinationScope.id).filter_by(destination_id=destination_id, code=code).first() is not None


def snapshot(scope: DestinationScope) -> dict[str, object]:
    fields = ("code", "name", "scope_type", "import_strategy", "bbox", "import_profile", "priority", "enabled")
    return {field: getattr(scope, field) for field in fields}
