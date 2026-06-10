from sqlalchemy.orm import Session

from models.place_scope_link import PlaceScopeLink


def link_place_to_scope(
    db: Session,
    place_id: int,
    scope_id: int,
    relation_type: str = "imported_from_scope",
) -> PlaceScopeLink:
    existing = db.query(PlaceScopeLink).filter_by(place_id=place_id, scope_id=scope_id).first()
    if existing is not None:
        return existing
    link = PlaceScopeLink(place_id=place_id, scope_id=scope_id, relation_type=relation_type)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
