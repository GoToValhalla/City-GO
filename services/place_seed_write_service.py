from sqlalchemy.orm import Session

from models.place import Place
from schemas.place_seed_item import PlaceSeedItem
from services.import_publication_gate import assess_import_quality
from services.place_change_review_service import propose_place_change
from services.place_seed_lookup_service import find_category_id, find_city_id, find_place_by_slug
from services.place_seed_payload_service import place_payload


def plan_place_seed_write(db: Session, item: PlaceSeedItem) -> str:
    city_id = find_city_id(db, item.city_slug)
    if city_id is None:
        return "invalid"
    return "updated" if find_place_by_slug(db, item.slug) is not None else "created"


def write_place_seed_item(db: Session, item: PlaceSeedItem) -> str:
    city_id = find_city_id(db, item.city_slug)
    if city_id is None:
        return "invalid"
    category_id = find_category_id(db, item.category)
    payload = place_payload(item, city_id, category_id)
    place = find_place_by_slug(db, item.slug)
    if place is None:
        # Качество импортируемого места определяет статус публикации.
        decision = assess_import_quality(
            title=item.title,
            lat=item.lat,
            lng=item.lng,
            category=item.category,
            confidence=item.confidence,
            source=item.source,
            address=item.address,
            opening_hours=item.opening_hours,
        )
        pub_fields = {
            "is_published": decision.is_published,
            "is_visible_in_catalog": decision.is_visible_in_catalog,
            "is_route_eligible": decision.is_route_eligible,
            "is_searchable": decision.is_searchable,
            "publication_status": decision.publication_status,
        }
        db.add(Place(**payload, **pub_fields))
        return decision.decision  # "auto_publish" | "needs_review" | "hidden"
    if not propose_place_change(db, place=place, proposed=payload, reason="place_seed_reimport"):
        return "queued_for_review"
    _update_place(place, payload)
    return "updated"


def _update_place(place: Place, payload: dict[str, object]) -> None:
    tuple(map(lambda item: setattr(place, item[0], item[1]), payload.items()))
