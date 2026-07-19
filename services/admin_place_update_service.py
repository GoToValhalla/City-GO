"""Update ordinary Place fields from the admin surface.

Publication, verification and route-state fields are rejected fail-closed and
must use their dedicated mutation services.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from core.place_category_hierarchy import CATEGORY_LABELS_RU, ROUTE_EXCLUDED_CATEGORIES
from core.publication_state_ownership import CONTROLLED_PLACE_INPUT_FIELDS
from models.category import Category
from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.product_event_service import record_event
from services.taxonomy_workflow_service import run_workflow

_ALLOWED = frozenset(
    {
        "title", "category", "canonical_category", "address", "short_description",
        "image_url", "lat", "lng", "source", "source_url", "website", "phone",
        "atmosphere", "inside", "best_for", "opening_hours",
        "average_visit_duration_minutes", "price_level", "indoor", "outdoor",
        "dog_friendly", "family_friendly", "admin_comment", "address_source",
        "address_confidence",
    }
)
_CONTROLLED_FIELDS = CONTROLLED_PLACE_INPUT_FIELDS
_DERIVED_STATE_INPUT_FIELDS = (_ALLOWED - {"admin_comment"}) | {"tag_ids"}


def update_admin_place_fields(
    db: Session,
    place_id: int,
    fields: dict[str, object],
    *,
    actor: str,
    commit: bool = True,
    locked_place: Place | None = None,
) -> Place | None:
    """Update ordinary data only; caller owns the transaction when commit=False."""

    try:
        updates = dict(fields)
        reason = updates.pop("reason", None)
        forbidden = sorted(set(updates).intersection(CONTROLLED_PLACE_INPUT_FIELDS))
        if forbidden:
            raise ValueError(
                "Управляемые поля состояния нельзя изменять через общий endpoint: "
                + ", ".join(forbidden)
            )
        unsupported = sorted(set(updates) - _ALLOWED - {"tag_ids"})
        if unsupported:
            raise ValueError("Неподдерживаемые поля места: " + ", ".join(unsupported))

        requested_derived_change = bool(set(updates).intersection(_DERIVED_STATE_INPUT_FIELDS))
        place = locked_place
        if place is None:
            query = db.query(Place).filter(Place.id == place_id)
            if requested_derived_change:
                query = query.order_by(Place.id.asc()).populate_existing().with_for_update()
            place = query.one_or_none()
        if place is None:
            return None
        if int(place.id) != int(place_id):
            raise ValueError("Переданный locked_place не соответствует place_id")

        category_changed = "category" in updates or "canonical_category" in updates
        if "category" in updates and "canonical_category" not in updates:
            updates["canonical_category"] = str(updates.get("category")) if updates.get("category") else None

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

        if "lat" in updates or "lng" in updates:
            target_lat = place.lat if "lat" not in updates else updates["lat"]
            target_lng = place.lng if "lng" not in updates else updates["lng"]
            if target_lat is not None and target_lng is not None:
                lat = float(target_lat)
                lng = float(target_lng)
                if abs(lat) < 0.000001 and abs(lng) < 0.000001:
                    raise ValueError("Нельзя сохранить место с координатами 0,0")

        ordinary_changes = {
            key: value
            for key, value in updates.items()
            if key in _ALLOWED and getattr(place, key) != value
        }
        old_tag_ids: list[int] | None = None
        new_tag_ids: list[int] | None = None
        if "tag_ids" in updates:
            old_tag_ids = sorted(
                row.tag_id for row in db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()
            )
            new_tag_ids = sorted({int(tag_id) for tag_id in updates["tag_ids"] or []})

        tags_changed = old_tag_ids is not None and old_tag_ids != new_tag_ids
        if not ordinary_changes and not tags_changed:
            raise ValueError("Нет фактических изменений")

        old_value = {key: getattr(place, key) for key in ordinary_changes}
        if old_tag_ids is not None:
            old_value["tag_ids"] = old_tag_ids
        for key, value in ordinary_changes.items():
            setattr(place, key, value)

        if tags_changed:
            db.query(PlaceTag).filter(PlaceTag.place_id == place_id).delete()
            for tag_id in new_tag_ids or []:
                db.add(PlaceTag(place_id=place_id, tag_id=tag_id))

        new_value = dict(ordinary_changes)
        if new_tag_ids is not None:
            new_value["tag_ids"] = new_tag_ids
        write_admin_audit_log(
            db,
            actor=actor,
            action="update_place_admin",
            entity_type="place",
            entity_id=place.id,
            old_value=old_value,
            new_value=new_value,
            reason=str(reason) if reason else None,
        )
        record_event(db, event_type="place_updated", place_id=place.id, commit=False)

        derived_changed = bool(set(ordinary_changes).intersection(_DERIVED_STATE_INPUT_FIELDS)) or tags_changed
        if derived_changed:
            request_id = uuid4().hex
            operation = run_workflow(
                db,
                workflow="after_place_update",
                request_id=request_id,
                idempotency_key=f"place-update:{place.id}:{request_id}",
                entity_type="place",
                entity_id=str(place.id),
                payload={
                    "source": "admin_place_update",
                    "changed_fields": sorted(new_value),
                },
                actor=actor,
                commit=False,
            )
            if operation.status != "completed":
                raise ValueError(operation.error_message or "Workflow обновления места завершился ошибкой")

        if commit:
            db.commit()
            db.refresh(place)
        else:
            db.flush()
        return place
    except Exception:
        if commit:
            db.rollback()
        raise
