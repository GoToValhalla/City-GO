"""Обновление непубликационных полей места из админки.

Publication-state fields are deliberately rejected here. Publish, unpublish,
hide, review and route-eligibility actions must use their explicit services,
which delegate to ``publication_state_writer`` and create transition lineage.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from core.place_category_hierarchy import CATEGORY_LABELS_RU, ROUTE_EXCLUDED_CATEGORIES
from models.category import Category
from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.place_service import get_place_by_id
from services.product_event_service import record_event
from services.taxonomy_workflow_service import run_workflow

_ALLOWED = frozenset(
    {
        "title",
        "category",
        "canonical_category",
        "address",
        "short_description",
        "image_url",
        "lat",
        "lng",
        "source",
        "source_url",
        "website",
        "phone",
        "atmosphere",
        "inside",
        "best_for",
        "opening_hours",
        "average_visit_duration_minutes",
        "price_level",
        "indoor",
        "outdoor",
        "dog_friendly",
        "family_friendly",
        "verification_status",
        "admin_comment",
        "route_exclusion_reason",
        "address_source",
        "address_confidence",
    }
)

# These fields form or influence the publication state machine. Accepting any of
# them in a generic setattr service recreates the exact bypass this architecture
# is intended to eliminate.
_PUBLICATION_CONTROLLED_FIELDS = frozenset(
    {
        "is_active",
        "status",
        "publication_status",
        "is_published",
        "is_visible_in_catalog",
        "is_searchable",
        "is_route_eligible",
        "visible_to_users",
        "searchable",
        "route_enabled",
        "published_at",
        "unpublished_at",
        "publication_reason_code",
        "publication_reason_details",
        "publication_comment",
    }
)


def update_admin_place_fields(
    db: Session,
    place_id: int,
    fields: dict[str, object],
    *,
    actor: str,
    commit: bool = True,
    locked_place: Place | None = None,
) -> Place | None:
    """Update only ordinary place data.

    The caller may pass a deterministically pre-locked Place and ``commit=False``
    for a larger caller-owned transaction. This function never owns publication
    state and fails closed when publication-controlled fields are supplied.
    """

    place = locked_place or get_place_by_id(db, place_id)
    if place is None:
        return None
    if int(place.id) != int(place_id):
        raise ValueError("Переданный locked_place не соответствует place_id")

    updates = dict(fields)
    reason = updates.pop("reason", None)
    forbidden = sorted(set(updates).intersection(_PUBLICATION_CONTROLLED_FIELDS))
    if forbidden:
        raise ValueError(
            "Поля публикации нельзя изменять через общий endpoint: " + ", ".join(forbidden)
        )

    unsupported = sorted(set(updates) - _ALLOWED - {"tag_ids"})
    if unsupported:
        raise ValueError("Неподдерживаемые поля места: " + ", ".join(unsupported))

    category_changed = "category" in updates or "canonical_category" in updates
    if "category" in updates and "canonical_category" not in updates:
        updates["canonical_category"] = (
            str(updates.get("category")) if updates.get("category") else None
        )

    if category_changed:
        code = str(updates.get("canonical_category") or updates.get("category") or "").strip().lower()
        if not code:
            raise ValueError("Категория не может быть пустой")
        category = db.query(Category).filter(Category.code == code).first()
        if category is None:
            eligible = code not in ROUTE_EXCLUDED_CATEGORIES
            category = Category(
                code=code,
                name=CATEGORY_LABELS_RU.get(code, code.replace("_", " ").title()),
                user_name=CATEGORY_LABELS_RU.get(code),
                is_active=True,
                is_catalog_visible=True,
                is_searchable=True,
                is_route_eligible=eligible,
                route_policy="allowed_by_context" if eligible else "useful_only",
                route_contexts=[],
            )
            db.add(category)
            db.flush()
        elif not category.is_active:
            raise ValueError("Выбранная категория архивирована")
        place.category_id = category.id
        updates["category"] = category.code
        updates["canonical_category"] = category.code

    if updates.get("lat") is not None and updates.get("lng") is not None:
        lat = float(updates["lat"])
        lng = float(updates["lng"])
        if abs(lat) < 0.000001 and abs(lng) < 0.000001:
            raise ValueError("Нельзя сохранить место с координатами 0,0")

    old = {key: getattr(place, key) for key in updates if key in _ALLOWED}
    old["tag_ids"] = (
        [row.tag_id for row in db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()]
        if "tag_ids" in updates
        else None
    )

    for key, value in updates.items():
        if key in _ALLOWED:
            setattr(place, key, value)

    if "tag_ids" in updates:
        db.query(PlaceTag).filter(PlaceTag.place_id == place_id).delete()
        for tag_id in updates["tag_ids"] or []:
            db.add(PlaceTag(place_id=place_id, tag_id=int(tag_id)))

    write_admin_audit_log(
        db,
        actor=actor,
        action="update_place_admin",
        entity_type="place",
        entity_id=place.id,
        old_value=old,
        new_value=updates,
        reason=str(reason) if reason else None,
    )
    record_event(db, event_type="place_updated", place_id=place.id, commit=False)

    if commit:
        db.commit()
        db.refresh(place)
        if category_changed:
            run_workflow(
                db,
                workflow="after_category_change",
                request_id=uuid4().hex,
                idempotency_key=f"category:{place.id}:{place.updated_at}",
                entity_type="place",
                entity_id=str(place.id),
                payload={},
                actor=actor,
            )
    else:
        db.flush()

    return place
