from sqlalchemy.orm import Session

from models.city import City
from models.place_discovery_request import PlaceDiscoveryRequest
from schemas.place_discovery import PlaceDiscoveryCreate


def create_discovery_request(db: Session, payload: PlaceDiscoveryCreate) -> PlaceDiscoveryRequest:
    city = db.query(City).filter(City.slug == payload.city_slug).first()
    if city is None:
        raise ValueError("unknown_city")
    item = PlaceDiscoveryRequest(
        city_id=city.id,
        name=payload.name,
        source_type=payload.source_type,
        address=payload.address,
        lat=payload.lat,
        lng=payload.lng,
        category_hint=payload.category_hint,
        submitted_by_telegram_user_id=payload.submitted_by_telegram_user_id,
        status="new",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
