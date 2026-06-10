"""
Места в радиусе от точки: выборка публично видимых Place из БД
и фильтр по формуле Haversine без PostGIS.
"""

from math import atan2, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from models.place import Place
from services.place_card_payload_service import place_card_payload
from services.place_public_image_attach_service import attach_public_images
from services.place_public_visibility import apply_public_place_visibility


# Вычисляет расстояние между двумя точками на земле в километрах.
def haversine_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c


# Возвращает список публично видимых мест рядом с переданной точкой.
def get_nearby_places(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float = 3.0,
) -> list[dict]:
    query = db.query(Place)
    places = attach_public_images(db, apply_public_place_visibility(query).all())

    results: list[dict] = []

    for place in places:
        distance_km = haversine_distance(lat, lng, place.lat, place.lng)

        if distance_km <= radius_km:
            results.append(
                {
                    **place_card_payload(place),
                    "lat": place.lat,
                    "lng": place.lng,
                    "distance_km": round(distance_km, 3),
                }
            )

    results.sort(key=lambda item: item["distance_km"])
    return results
