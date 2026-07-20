"""Explicit, auditable reconciliation of legacy public-city flags."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.feature_toggle import FeatureToggle
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.admin_city_publication_service import publish_city
from services.place_public_visibility import public_place_conditions
from services.publication_state_writer import (
    InvalidPublicationTransition,
    REASON_ADMIN_UNPUBLISH,
    REASON_PUBLISHED,
    REASON_REPAIR_STATE,
    transition_place_publication,
)

PUBLIC_CITY_STATUS = "published"
RECONCILIATION_ACTION = "reconcile_publication_flags"
CITY_VISIBILITY_TOGGLE = "city_visible_to_users"


def publication_reconciliation_snapshot(db: Session) -> dict[str, object]:
    cities: list[dict[str, object]] = []
    leaked_place_ids: list[int] = []
    partial_place_ids: list[int] = []

    for city in db.query(City).order_by(City.name.asc(), City.id.asc()).all():
        places = db.query(Place).filter(Place.city_id == city.id).all()
        city_is_public = bool(city.is_active and city.launch_status == PUBLIC_CITY_STATUS)
        public_places = sum(1 for place in places if _is_fully_public(place))
        leaked = [place for place in places if not city_is_public and _has_any_public_flag(place)]
        partial = [place for place in places if city_is_public and _has_partial_public_flags(place)]
        leaked_place_ids.extend(place.id for place in leaked)
        partial_place_ids.extend(place.id for place in partial)
        cities.append(
            {
                "city_id": city.id,
                "city_slug": city.slug,
                "city_name": city.name,
                "launch_status": city.launch_status,
                "is_active": bool(city.is_active),
                "is_public": city_is_public,
                "places_total": len(places),
                "public_places": public_places,
                "city_visibility_toggle": _city_visibility_toggle_value(db, city.slug),
                "leaked_place_ids": [place.id for place in leaked],
                "partial_public_place_ids": [place.id for place in partial],
            }
        )

    public_city_rows = db.query(City).filter(City.is_active.is_(True), City.launch_status == PUBLIC_CITY_STATUS).count()
    public_place_rows = db.query(Place).filter(*public_place_conditions()).count()
    return {
        "public_cities": public_city_rows,
        "public_places": public_place_rows,
        "cities": cities,
        "violations": {
            "places_public_in_unpublished_city": leaked_place_ids,
            "partial_public_flags_in_published_city": partial_place_ids,
        },
        "rollback": {
            "supported": True,
            "instruction": "Use POST /admin/publication-reconciliation/rollback with audit_ids returned by apply.",
        },
    }


def materialize_legacy_city_visibility_defaults(
    db: Session,
    *,
    actor: str,
    cutoff: datetime,
    reason: str | None = None,
) -> dict[str, object]:
    """Persist the old admin default=true city visibility state for legacy cities."""
    created: list[str] = []
    cities = db.query(City).filter(City.created_at <= cutoff).order_by(City.slug.asc()).all()
    for city in cities:
        exists = db.query(FeatureToggle.id).filter(
            FeatureToggle.scope == "city",
            FeatureToggle.scope_id == city.slug,
            FeatureToggle.key == CITY_VISIBILITY_TOGGLE,
        ).first()
        if exists is not None:
            continue
        row = FeatureToggle(
            key=CITY_VISIBILITY_TOGGLE,
            scope="city",
            scope_id=city.slug,
            value_bool=True,
            description="Materialized legacy admin default before city publication toggle became explicit.",
            updated_by=actor,
            change_reason=reason or "legacy city visibility default materialization",
        )
        db.add(row)
        db.flush()
        write_admin_audit_log(
            db,
            actor=actor,
            action="materialize_legacy_city_visibility_toggle",
            entity_type="feature_toggle",
            entity_id=f"city:{city.slug}:{CITY_VISIBILITY_TOGGLE}",
            old_value={"value_bool": None},
            new_value={"value_bool": True, "city_slug": city.slug, "cutoff": cutoff.isoformat()},
            reason=reason or "legacy city visibility default materialization",
        )
        created.append(city.slug)
    db.commit()
    return {"created_city_visibility_toggles": created}


def apply_city_visibility_toggle_reconciliation(
    db: Session,
    *,
    actor: str,
    city_slugs: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Apply legacy admin city_visible_to_users toggles to real city publication."""
    toggle_query = db.query(FeatureToggle).filter(
        FeatureToggle.scope == "city",
        FeatureToggle.key == CITY_VISIBILITY_TOGGLE,
        FeatureToggle.value_bool.is_(True),
    )
    if city_slugs:
        toggle_query = toggle_query.filter(FeatureToggle.scope_id.in_(city_slugs))

    published: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    for toggle in toggle_query.order_by(FeatureToggle.scope_id.asc()).all():
        city = db.query(City).filter(City.slug == toggle.scope_id).first()
        if city is None:
            failed.append({"city_slug": toggle.scope_id, "reason": "city_not_found"})
            continue
        if city.is_active and city.launch_status == PUBLIC_CITY_STATUS:
            continue
        try:
            result = publish_city(
                db,
                city.id,
                actor=actor,
                reason=reason or "legacy city_visible_to_users=true reconciliation",
            )
        except ValueError as exc:
            failed.append({"city_slug": city.slug, "reason": str(exc)})
            continue
        if result is not None:
            published.append(
                {
                    "city_slug": result.city.slug,
                    "city_name": result.city.name,
                    "places_total": result.places_total,
                    "places_published": result.places_published,
                    "places_hidden": result.places_hidden,
                }
            )

    return {
        "published_cities": published,
        "failed_cities": failed,
        "snapshot": publication_reconciliation_snapshot(db),
    }


def apply_publication_reconciliation(
    db: Session,
    *,
    actor: str,
    city_slugs: list[str] | None = None,
    reason: str | None = None,
    allow_destructive: bool = False,
) -> dict[str, object]:
    """Reconcile publication flags without destructive resets by default.

    Import/reconciliation must not hide already published places just because a
    city import failed or product city state is temporarily wrong. The default
    behavior is a dry diagnostic apply: report leaked public flags and repair
    partial flags for places whose publication_status is already published.
    Destructive hide remains available only for explicit admin repair calls that
    pass allow_destructive=True with a reason.
    """
    query = db.query(City)
    if city_slugs:
        query = query.filter(City.slug.in_(city_slugs))

    changed_audit_ids: list[int] = []
    changed_places = 0
    skipped_destructive = 0
    for city in query.order_by(City.id.asc()).all():
        for place in db.query(Place).filter(Place.city_id == city.id).all():
            if place.publication_status == PUBLIC_CITY_STATUS and _has_partial_public_flags(place):
                old_value = _public_flags(place)
                _restore_published_place_flags(db, place, actor=actor, source="publication_reconciliation")
                audit = write_admin_audit_log(
                    db,
                    actor=actor,
                    action=RECONCILIATION_ACTION,
                    entity_type="place",
                    entity_id=place.id,
                    old_value={"city_slug": city.slug, **old_value},
                    new_value={"city_slug": city.slug, **_public_flags(place)},
                    reason=reason or "restore_published_place_public_flags",
                )
                db.flush()
                changed_audit_ids.append(audit.id)
                changed_places += 1
                continue

            city_is_public = bool(city.is_active and city.launch_status == PUBLIC_CITY_STATUS)
            if city_is_public or not _has_any_public_flag(place):
                continue
            if not allow_destructive:
                skipped_destructive += 1
                continue
            if not reason:
                raise ValueError("Destructive publication reconciliation requires explicit reason")
            old_value = _public_flags(place)
            _hide_place(db, place, actor=actor, source="publication_reconciliation", reason=reason)
            audit = write_admin_audit_log(
                db,
                actor=actor,
                action=RECONCILIATION_ACTION,
                entity_type="place",
                entity_id=place.id,
                old_value={"city_slug": city.slug, **old_value},
                new_value={"city_slug": city.slug, **_public_flags(place)},
                reason=reason,
            )
            db.flush()
            changed_audit_ids.append(audit.id)
            changed_places += 1

    db.commit()
    return {
        "changed_places": changed_places,
        "skipped_destructive": skipped_destructive,
        "audit_ids": changed_audit_ids,
        "snapshot": publication_reconciliation_snapshot(db),
    }


def rollback_publication_reconciliation(
    db: Session,
    *,
    audit_ids: list[int],
    actor: str,
    reason: str,
) -> dict[str, object]:
    restored = 0
    missing_ids: list[int] = []
    for audit in db.query(AdminAuditLog).filter(
        AdminAuditLog.id.in_(list(dict.fromkeys(audit_ids))),
        AdminAuditLog.action == RECONCILIATION_ACTION,
        AdminAuditLog.entity_type == "place",
    ).all():
        place = db.query(Place).filter(Place.id == int(audit.entity_id or 0)).first()
        old_value = dict(audit.old_value or {})
        if place is None:
            missing_ids.append(audit.id)
            continue
        previous = _public_flags(place)
        _restore_place_from_snapshot(db, place, old_value, actor=actor)
        write_admin_audit_log(
            db,
            actor=actor,
            action="rollback_publication_reconciliation",
            entity_type="place",
            entity_id=place.id,
            old_value={"reconciliation_audit_id": audit.id, **previous},
            new_value={"reconciliation_audit_id": audit.id, **_public_flags(place)},
            reason=reason,
        )
        restored += 1

    db.commit()
    return {"restored_places": restored, "missing_audit_ids": missing_ids}


_PUBLIC_FLAG_FIELDS = (
    "is_published",
    "is_visible_in_catalog",
    "is_searchable",
    "is_route_eligible",
    "publication_status",
)


def _city_visibility_toggle_value(db: Session, city_slug: str) -> bool | None:
    return db.query(FeatureToggle.value_bool).filter(
        FeatureToggle.scope == "city",
        FeatureToggle.scope_id == city_slug,
        FeatureToggle.key == CITY_VISIBILITY_TOGGLE,
    ).scalar()


def _public_flags(place: Place) -> dict[str, object]:
    return {field: getattr(place, field) for field in _PUBLIC_FLAG_FIELDS}


def _has_any_public_flag(place: Place) -> bool:
    return bool(place.is_published or place.is_visible_in_catalog or place.is_searchable or place.is_route_eligible)


def _is_fully_public(place: Place) -> bool:
    return bool(place.is_published and place.is_visible_in_catalog and place.is_searchable and place.publication_status == PUBLIC_CITY_STATUS)


def _has_partial_public_flags(place: Place) -> bool:
    values = (bool(place.is_published), bool(place.is_visible_in_catalog), bool(place.is_searchable))
    return any(values) and not all(values)


def _restore_published_place_flags(db: Session, place: Place, *, actor: str, source: str) -> None:
    try:
        transition_place_publication(
            db,
            place,
            to_status=PUBLIC_CITY_STATUS,
            reason_code=REASON_PUBLISHED,
            actor=actor,
            source=source,
            human_comment=place.publication_comment,
            route_eligible_when_published=True,
        )
    except InvalidPublicationTransition:
        pass


def _hide_place(db: Session, place: Place, *, actor: str, source: str, reason: str) -> None:
    try:
        transition_place_publication(
            db,
            place,
            to_status="unpublished",
            reason_code=REASON_ADMIN_UNPUBLISH,
            actor=actor,
            source=source,
            human_comment=reason,
        )
    except InvalidPublicationTransition:
        pass


def _restore_place_from_snapshot(db: Session, place: Place, snapshot: dict[str, object], *, actor: str) -> None:
    target_status = str(snapshot.get("publication_status") or "draft")
    target_route_eligible = bool(snapshot.get("is_route_eligible"))
    try:
        if target_status == PUBLIC_CITY_STATUS:
            transition_place_publication(
                db,
                place,
                to_status=PUBLIC_CITY_STATUS,
                reason_code=REASON_PUBLISHED,
                actor=actor,
                source="publication_reconciliation_rollback",
                human_comment=place.publication_comment,
                route_eligible_when_published=target_route_eligible,
                route_exclusion_reason_when_published=None if target_route_eligible else "reconciliation_rollback",
            )
        else:
            transition_place_publication(
                db,
                place,
                to_status=target_status,
                reason_code=REASON_REPAIR_STATE,
                actor=actor,
                source="publication_reconciliation_rollback",
            )
    except InvalidPublicationTransition:
        pass
