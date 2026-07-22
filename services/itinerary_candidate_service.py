"""LEGACY ITINERARY CANDIDATE SERVICE.

Status: part of the old `/routes/generate` itinerary stack.

Active candidate retrieval source of truth:
- `services.candidate_retrieval_service`
- `services.route_builder_flow`
- route eligibility query filters.

Rules:
- Do not add new retrieval/filtering product logic here.
- Keep only for old itinerary endpoint compatibility until consumers migrate.
"""

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.itinerary_time_service import is_place_closed_all_day
from services.city_place_filters import apply_city_quality_filters
from services.route_eligibility import (
    apply_public_route_eligible_filters,
    evaluate_place_route_eligibility,
    is_route_forbidden_category,
)
from services.feature_toggle_service import is_toggle_enabled
from services.routing_projection_candidate_service import ROUTING_PROJECTION_TOGGLE, routing_projection_candidates
from types import SimpleNamespace


# Получает город по slug.
def get_city_by_slug(db: Session, city_slug: str) -> City | None:
    return db.query(City).filter(City.slug == city_slug).first()


# Проверяет, проходит ли место по базовым фильтрам.
def passes_basic_filters(place: Place, merged_context: dict) -> bool:
    if not place.is_active:
        return False

    if place.status != "active":
        return False

    if is_route_forbidden_category(place.category):
        return False

    eligibility = evaluate_place_route_eligibility(place)
    if not eligibility.eligible:
        return False

    # Indoor / outdoor фильтры.
    if merged_context.get("indoor_only"):
        if place.category in ("walk", "park", "viewpoint", "beach"):
            return False

    if merged_context.get("outdoor_only"):
        if place.category in ("museum", "gallery", "cafe", "restaurant"):
            return False

    # Budget фильтр.
    budget_level = merged_context.get("budget_level")
    if budget_level is not None:
        if place.price_level is not None and place.price_level > budget_level:
            return False

    return True


# Основная функция получения кандидатов.
def get_candidate_places(
    db: Session,
    request,
    merged_context: dict,
    start_context,
) -> list[Place]:
    if is_toggle_enabled(db, ROUTING_PROJECTION_TOGGLE, default=False):
        location = (getattr(start_context, "lat", None), getattr(start_context, "lng", None))
        if None in location:
            location = None
        ctx = SimpleNamespace(
            city_id=request.city_slug, location=location, radius_meters=getattr(request, "radius_meters", 0),
            avoided_place_ids=[], avoided_categories=[], destination_id=getattr(request, "destination_id", None),
        )
        return [row for row in routing_projection_candidates(db, ctx) if passes_basic_filters(row, merged_context)]
    city = get_city_by_slug(db, request.city_slug)
    if city is None:
        return []

    query = db.query(Place).filter(
        Place.city_id == city.id,
    )
    query = apply_public_route_eligible_filters(query)
    query = apply_city_quality_filters(query, db, city_slug=city.slug)

    places = query.all()

    # Базовая фильтрация.
    filtered_places = [
        place for place in places if passes_basic_filters(place, merged_context)
    ]

    # Time-aware фильтр (день, а не момент).
    trip_start_datetime = merged_context.get("trip_start_datetime")

    if trip_start_datetime is not None:
        time_filtered = []

        for place in filtered_places:
            closed_all_day = is_place_closed_all_day(
                place=place,
                dt=trip_start_datetime,
            )

            # Если явно закрыто весь день — выкидываем.
            if closed_all_day is True:
                continue

            time_filtered.append(place)

        return time_filtered

    return filtered_places
