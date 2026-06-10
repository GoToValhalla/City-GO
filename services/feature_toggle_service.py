"""Чтение и запись feature toggles."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.feature_toggle import FeatureToggle
from services.admin_audit_service import write_admin_audit_log
from services.feature_toggle_catalog import CITY_TOGGLES, GLOBAL_TOGGLES, GROUP_LABELS
from services.feature_toggle_catalog.types import ToggleDef


def _find_row(db: Session, *, key: str, scope: str, scope_id: str | None) -> FeatureToggle | None:
    return db.query(FeatureToggle).filter(
        FeatureToggle.key == key, FeatureToggle.scope == scope, FeatureToggle.scope_id == scope_id,
    ).first()


def _default_for(key: str, catalog: tuple[ToggleDef, ...]) -> bool:
    return next((item["default"] for item in catalog if item["key"] == key), False)


def is_toggle_enabled(db: Session, key: str, *, scope: str = "global", scope_id: str | None = None, default: bool | None = None) -> bool:
    row = _find_row(db, key=key, scope=scope, scope_id=scope_id)
    if row is not None:
        return row.value_bool
    if default is not None:
        return default
    catalog = GLOBAL_TOGGLES if scope == "global" else CITY_TOGGLES
    return _default_for(key, catalog)


def list_global_toggles(db: Session) -> list[dict[str, object]]:
    return [_payload(db, item) for item in GLOBAL_TOGGLES]


def list_city_toggles(db: Session, city_slug: str) -> list[dict[str, object]]:
    return [_payload(db, {**item, "scope_id": city_slug}, scope_id=city_slug) for item in CITY_TOGGLES]


def list_groups() -> list[dict[str, str]]:
    return [{"code": code, "label": GROUP_LABELS.get(code, code)} for code in GROUP_LABELS]


def update_toggle(
    db: Session, *, key: str, scope: str, scope_id: str | None, value_bool: bool, actor: str,
    reason: str | None = None, description: str | None = None,
) -> FeatureToggle:
    row = _find_row(db, key=key, scope=scope, scope_id=scope_id)
    old = None if row is None else row.value_bool
    if row is None:
        row = FeatureToggle(key=key, scope=scope, scope_id=scope_id, value_bool=value_bool, description=description)
        db.add(row)
    else:
        row.value_bool = value_bool
        if description:
            row.description = description
    row.updated_by = actor
    row.change_reason = reason
    write_admin_audit_log(
        db, actor=actor, action="update_feature_toggle", entity_type="feature_toggle",
        entity_id=f"{scope}:{scope_id or ''}:{key}", old_value={"value_bool": old},
        new_value={"value_bool": value_bool}, reason=reason,
    )
    db.commit()
    db.refresh(row)
    return row


def _payload(db: Session, item: ToggleDef, *, scope_id: str | None = None) -> dict[str, object]:
    row = _find_row(db, key=item["key"], scope=item["scope"], scope_id=scope_id)
    return {
        **item,
        "scope_id": scope_id,
        "value_bool": row.value_bool if row else item["default"],
        "default": item["default"],
        "updated_by": getattr(row, "updated_by", None),
        "updated_at": getattr(row, "updated_at", None),
    }
