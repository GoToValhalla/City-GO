"""Place query and generic persistence services."""

from uuid import uuid4

from sqlalchemy.orm import Session

from core.publication_state_ownership import CONTROLLED_PLACE_INPUT_FIELDS, PUBLICATION_OWNED_FIELDS
from models.place import Place
from schemas.place import PlaceCreate, PlaceUpdate
from schemas.place_query_params import PlaceQueryParams
from services.place_count_service import get_query_total
from services.place_filters_service import apply_place_filters
from services.place_public_visibility import apply_public_place_visibility
from services.place_query_params_service import normalize_place_query_params
from services.place_search_service import apply_place_text_search
from services.place_sorting_service import apply_place_sorting
from services.publication_state_writer import (
    REASON_ADMIN_CREATE_DRAFT,
    REASON_ADMIN_HIDE,
    transition_place_publication,
)
from services.taxonomy_workflow_service import run_workflow

PROTECTED_PUBLICATION_FIELDS = PUBLICATION_OWNED_FIELDS
PROTECTED_CONTROLLED_FIELDS = CONTROLLED_PLACE_INPUT_FIELDS
_DERIVED_PLACE_UPDATE_FIELDS = frozenset(
    {
        "category", "canonical_category", "lat", "lng", "address", "short_description",
        "image_url", "opening_hours", "average_visit_duration_minutes", "price_level",
        "indoor", "outdoor", "dog_friendly", "family_friendly",
    }
)


def _place_column_payload(payload: dict) -> dict:
    allowed_fields = {
        column.name
        for column in Place.__table__.columns
        if column.name not in CONTROLLED_PLACE_INPUT_FIELDS
    }
    return {key: value for key, value in payload.items() if key in allowed_fields}


def get_places(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    destination_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    sort_order: str = "asc",
    public_only: bool = True,
) -> list[Place]:
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            destination_slug=destination_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )
    query = db.query(Place)
    if public_only:
        query = apply_public_place_visibility(query)
    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        destination_slug=params.destination_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return []
    query = apply_place_text_search(query, params.q)
    query = apply_place_sorting(query=query, params=params)
    return query.offset(params.offset).limit(params.limit).all()


def get_places_total(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    destination_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    public_only: bool = True,
) -> int:
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            destination_slug=destination_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
        )
    )
    query = db.query(Place)
    if public_only:
        query = apply_public_place_visibility(query)
    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        destination_slug=params.destination_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return 0
    query = apply_place_text_search(query, params.q)
    return get_query_total(query)


def get_place_by_id(db: Session, place_id: int, *, public_only: bool = False) -> Place | None:
    query = db.query(Place).filter(Place.id == place_id)
    if public_only:
        query = apply_public_place_visibility(query)
    return query.first()


def get_place_by_slug(db: Session, slug: str, *, public_only: bool = False) -> Place | None:
    query = db.query(Place).filter(Place.slug == slug)
    if public_only:
        query = apply_public_place_visibility(query)
    return query.first()


def create_place(
    db: Session,
    place_in: PlaceCreate,
    *,
    actor: str = "place_service",
    commit: bool = True,
) -> Place:
    try:
        place = Place(**_place_column_payload(place_in.model_dump()))
        db.add(place)
        db.flush()
        transition_place_publication(
            db,
            place,
            to_status="draft",
            reason_code=REASON_ADMIN_CREATE_DRAFT,
            actor=actor,
            source="place_create",
            reason_details={"origin": "generic_place_create"},
            human_comment="Created as unpublished draft",
            lock_place=False,
        )
        _shadow_write_membership(db, place)
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


def _shadow_write_membership(db: Session, place: Place) -> None:
    from models.city import City
    from services.city_destination_compatibility import get_destination_for_city
    from services.destination_flags import destination_import_enabled
    from services.destination_membership_service import upsert_membership

    city = db.query(City).filter(City.id == place.city_id).first()
    if city is None:
        return
    destination = get_destination_for_city(db, city)
    if destination is None:
        return
    upsert_membership(
        db,
        place_id=place.id,
        destination_id=destination.id,
        assignment_type="legacy_city" if not destination_import_enabled() else "imported",
        is_primary=True,
        source="place_write_shadow",
    )
    db.flush()


def update_place(
    db: Session,
    place_id: int,
    place_in: PlaceUpdate,
    *,
    actor: str = "place_service",
    commit: bool = True,
) -> Place | None:
    try:
        place = (
            db.query(Place)
            .filter(Place.id == place_id)
            .populate_existing()
            .with_for_update()
            .one_or_none()
        )
        if place is None:
            return None
        payload = _place_column_payload(place_in.model_dump(exclude_unset=True))
        changes = {field: value for field, value in payload.items() if getattr(place, field) != value}
        if not changes:
            return place

        for field, value in changes.items():
            setattr(place, field, value)
        if "lat" in changes or "lng" in changes:
            from services.destination_membership_service import mark_place_stale

            mark_place_stale(db, place.id)

        derived_changed = bool(set(changes).intersection(_DERIVED_PLACE_UPDATE_FIELDS))
        if derived_changed:
            db.flush()
            request_id = uuid4().hex
            operation = run_workflow(
                db,
                workflow="after_place_update",
                request_id=request_id,
                idempotency_key=f"legacy-place-update:{place.id}:{request_id}",
                entity_type="place",
                entity_id=str(place.id),
                payload={"source": "place_service", "changed_fields": sorted(changes)},
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


def delete_place(
    db: Session,
    place_id: int,
    *,
    actor: str = "place_service",
    reason: str = "Deleted through generic place API",
    commit: bool = True,
) -> bool:
    """Soft-delete through the canonical publication state machine; never erase history."""
    try:
        place = (
            db.query(Place)
            .filter(Place.id == place_id)
            .populate_existing()
            .with_for_update()
            .one_or_none()
        )
        if place is None:
            return False
        if (
            place.publication_status == "hidden"
            and place.publication_reason_code == REASON_ADMIN_HIDE
            and not place.is_published
            and not place.is_visible_in_catalog
            and not place.is_searchable
            and not place.is_route_eligible
        ):
            return True
        transition_place_publication(
            db,
            place,
            to_status="hidden",
            reason_code=REASON_ADMIN_HIDE,
            actor=actor,
            source="place_delete",
            reason_details={"soft_delete": True},
            human_comment=reason,
            lock_place=False,
        )
        if commit:
            db.commit()
            db.refresh(place)
        else:
            db.flush()
        return True
    except Exception:
        if commit:
            db.rollback()
        raise
