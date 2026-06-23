from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.place_schedule import PlaceSchedule
from services.place_card_payload_service import place_card_payload
from services.place_public_image_attach_service import attach_public_images
from services.place_public_visibility import apply_public_place_visibility


# Возвращает код текущего дня недели.
def get_weekday_code(dt: datetime) -> str:
    weekday_map = {
        0: "mon",
        1: "tue",
        2: "wed",
        3: "thu",
        4: "fri",
        5: "sat",
        6: "sun",
    }
    return weekday_map[dt.weekday()]


# Возвращает список публичных мест, которые открыты сейчас в выбранном городе.
def get_open_now_places(
    db: Session,
    city_slug: str,
) -> list[dict]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    now = datetime.now(ZoneInfo(city.timezone))
    weekday_code = get_weekday_code(now)
    current_time = now.time()

    query = (
        db.query(Place)
        .join(PlaceSchedule, Place.id == PlaceSchedule.place_id)
        .filter(Place.city_id == city.id)
        .filter(PlaceSchedule.weekday == weekday_code)
        .filter(PlaceSchedule.is_closed.is_(False))
    )

    places = attach_public_images(db, apply_public_place_visibility(query).all())

    results: list[dict] = []

    for place in places:
        schedule = (
            db.query(PlaceSchedule)
            .filter(PlaceSchedule.place_id == place.id)
            .filter(PlaceSchedule.weekday == weekday_code)
            .first()
        )

        if schedule is None:
            continue

        if schedule.open_time is None or schedule.close_time is None:
            continue

        if not _opening_hours_trusted(db, place.id):
            continue

        if schedule.open_time <= current_time <= schedule.close_time:
            results.append(
                {
                    **place_card_payload(place),
                    "open_time": schedule.open_time.strftime("%H:%M"),
                    "close_time": schedule.close_time.strftime("%H:%M"),
                }
            )

    return results


def _opening_hours_trusted(db: Session, place_id: int) -> bool:
    row = (
        db.query(PlaceFieldConfidence)
        .filter(PlaceFieldConfidence.place_id == place_id, PlaceFieldConfidence.field_name == "opening_hours")
        .first()
    )
    if row is None:
        return True
    if row.confidence_level == "low" or row.freshness_status == "stale":
        return False
    return row.conflict_status in {None, "none"}
