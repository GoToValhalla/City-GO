from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.publication_state_writer import InvalidPublicationTransition, reconcile_published_place_state
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


def exclude_forbidden_categories(db: Session, city_slug: str, *, actor: str) -> dict[str, object]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise LookupError("Город не найден")
    places = db.query(Place).filter(
        Place.city_id == city.id, Place.category.in_(tuple(ROUTE_FORBIDDEN_CATEGORIES)),
        Place.is_route_eligible.is_(True),
    ).all()
    affected = sum(_reconcile(db, place, actor) for place in places if place.is_published)
    write_admin_audit_log(
        db, actor=actor, action="exclude_forbidden_route_categories", entity_type="city",
        entity_id=city.slug, old_value=None, new_value={"affected": affected},
        reason="data_quality_action",
    )
    db.commit()
    return {"city_slug": city.slug, "affected": affected, "status": "done",
            "reason": "forbidden_category_cleanup"}


def _reconcile(db: Session, place: Place, actor: str) -> int:
    try:
        changed = reconcile_published_place_state(
            db, place, route_eligible=False, route_exclusion_reason="forbidden_category_cleanup",
            actor=actor, source="admin_route_eligibility",
        )
    except InvalidPublicationTransition:
        return 0
    return int(changed)
